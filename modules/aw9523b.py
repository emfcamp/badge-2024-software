from machine import Pin

class AW9523BPin:
    """
    AW9523B Pin Class
    Should be mostly compatible with micropython's
    machine.Pin class. 
    Can be given to apps as a transparent interface
    for a GPIO pin
    """
    def __init__(self, chip, id, *args, **kwargs):
        self.chip = chip
        self.pin = id
        self.port = id[0]
        self.pin = id[1]
        self.init(*args, **kwargs)

    def init(self, mode=-1, pull=-1, value=None, drive=0):
        self.mode(mode)
        self.pull(pull)
        self.drive(drive)
        self.value(value)

    def value(self, *value):
        if len(value) == 0:
            return self.chip.pin_read(self.pin)
        value = value[0]
        self.chip.pin_write(self.pin, value)

    def __call__(self, *args):
        return self.value(*args)
    
    def on(self):
        self.value(True)

    def off(self):
        self.value(False)

    def irq(self, handler=None, trigger=Pin.IRQ_FALLING|Pin.IRQ_RISING):
        if trigger is None or handler is None:
            self.chip.set_irq_handler(self.pin, None, None)
            self.chip.pin_set_irq_enabled(self.pin, False)
            return
        
        def handler_wrapper(pinobj):
            pinstate = pinobj.value()
            if pinstate and (trigger&Pin.IRQ_RISING) or \
                not pinstate and (trigger&Pin.IRQ_FALLING):
                handler(pinobj)
        self.chip.set_irq_handler(self.pin, handler_wrapper, self)
        self.chip.pin_set_irq_enabled(self.pin, True)

    def low(self):
        self.value(False)

    def high(self):
        self.value(True)

    def mode(self, *mode):
        """
        We use ALT mode to represent LED driving ability
        of the AW9523B. This supports 255 levels of drive
        strength
        """
        if len(mode) == 0:
            mode = self.chip.pin_get_mode(self.pin)
            if mode == 0:
                return Pin.ALT
            return Pin.IN if self.chip.pin_get_direction(self.pin) else Pin.OUT
        mode = mode[0]
        if mode == Pin.ALT:
            self.chip.pin_set_mode(self.pin, 0)
            return
        if mode == Pin.IN or mode == Pin.OUT:
            self.chip.pin_set_mode(self.pin, 1)
        if mode == Pin.IN:
            self.chip.pin_set_direction(self.pin, True)
        elif mode == Pin.OUT:
            self.chip.pin_set_direction(self.pin, False)
            


    def pull(self, *pull):
        #does nothing currently
        pass

    def drive(self, *drive):
        """
        set the LED drive strength
        Does nothing in regular Pin.OUT mode
        """
        if len(drive) == 0:
            return self.chip.pin_get_drive(self.pin)
        drive = drive[0]
        self.chip.pin_set_drive(self.pin, drive)


class AW9523B:
    def __init__(self, bus, addr):
        self.bus = bus
        self.addr = addr

        self.port_get_input_value = AW9523B.port_getter(0x00)
        self.port_get_output_value = AW9523B.port_getter(0x02)
        self.port_set_output_value = AW9523B.port_setter(0x02)
        self.port_get_direction = AW9523B.port_getter(0x04)
        self.port_set_direction = AW9523B.port_setter(0x04)
        self.port_get_irq_enabled = AW9523B.port_getter(0x06)
        self.port_set_irq_enabled = AW9523B.port_setter(0x06)
        self.port_get_mode = AW9523B.port_getter(0x12)
        self.port_set_mode = AW9523B.port_setter(0x12)

        # self.pin_read = AW9523B.pin_getter(0x00)
        self.pin_write = AW9523B.pin_setter(0x02)
        self.pin_set_direction = AW9523B.pin_setter(0x04)
        self.pin_get_irq_enabled = AW9523B.pin_getter(0x06)
        self.pin_set_irq_enabled = AW9523B.pin_setter(0x06)
        self.pin_get_mode = AW9523B.pin_getter(0x12)
        self.pin_set_mode = AW9523B.pin_setter(0x12)

        self.port_values = [0,0]
        self.irq_handlers = [[None for _ in range(8)] for _ in range(2)]

    def init(self):
        #reset
        self.bus.writeto_mem(self.addr, 0x7f, bytes([0x00]))
        #disable interrupts
        self.bus.writeto_mem(self.addr, 0x06, bytes([0xff, 0xff]))
        #everything input
        self.bus.writeto_mem(self.addr, 0x04, bytes([0xff, 0xff]))
        #push-pull
        self.bus.writeto_mem(self.addr, 0x11, bytes([0x10]))


    def port_getter(cls, base):
        def getter(self, port):
            return int(self.bus.readfrom_mem(self.addr, base+port, 1)[0])
        return getter

    def port_setter(cls, base):
        def setter(self, port, value):
            return self.bus.writeto_mem(self.addr, base+port, bytes([value]))
        return setter
    
    def pin_getter(cls, base):
        port_getter = cls.port_getter(base)
        def getter(self, pin):
            return True if (port_getter(self, pin[0]) & (1<<pin[1])) else False
        return getter
    
    def pin_setter(cls, base):
        port_getter = cls.port_getter(base)
        port_setter = cls.port_setter(base)
        def setter(self, pin, value):
            portvalue = port_getter(self, pin[0])
            if value:
                portvalue |= (1<<pin[1])
            else:
                portvalue &= 0xff^(1<<pin[1])
            port_setter(self, pin[0], portvalue)
        return setter
            
    def pin_read(self, pin):
        value = self.port_get_input_value(pin[0])
        self.port_values[pin[0]] = value
    
    def pinidx(_, pin):
        if pin[0] == 0:
            return 4+pin[1]
        if pin[1] < 4:
            return pin[1]
        return 8+pin[1]
        
    def pin_set_drive(self, pin, drive):
        self.bus.writeto_mem(self.addr, 0x20+AW9523B.pinidx(pin), bytes([drive]))

    def pin_get_drive(self, pin):
        return int(self.bus.readto_mem(self.addr, 0x20+AW9523B.pinidx(pin), 1)[0])

    def check_irqs(self):
        irqs_enabled = list(map(int,self.bus.readfrom_mem(self.addr, 0x06, 2)))
        pin_values = list(map(int, self.bus.readfrom_mem(self.addr, 0x00, 2)))
        pins_changed = list(map(lambda a,b,c: (a^b)&c, zip(pin_values, self.port_values, irqs_enabled)))
        self.port_values = pin_values
        if sum(pins_changed) == 0:
            # quick out if nothing triggered
            return
        for port in range(2):
            for pin in range(8):
                if pins_changed[port]&(1<<pin) == 0:
                    continue
                handler = self.irq_handlers[port][pin]
                if handler is None:
                    continue
                handler[0](handler[1])

    def set_irq_handler(self, pin, handler, obj):
        if handler:
            self.irq_handlers[pin[0]][pin[1]] = (handler, obj)
        else:
            self.irq_handlers[pin[0]][pin[1]] = None