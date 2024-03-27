class TCA9548ABus:
    def __init__(self, chip, bus_no):
        self.chip = chip
        self.bus_no = bus_no

    def __getattr__(self, key):
        chip = getattr(self, "chip")
        bus_no = getattr(self, "bus_no")
        try:
            v = getattr(self, key)
            return v
        except:
            v = getattr(chip.bus, key)
            if callable(v):
                def wrapper(*args, **kwargs):
                    chip.select_downstream(bus_no)  
                    return v(*args, **kwargs)
                v = wrapper
            setattr(self, key, v)
            return v
        
class TCA9548A:

    def __init__(self, bus, addr):
        self.bus = bus
        self.addr = addr
        self.cur_i2c_bus = None
        self.downstreams = [TCA9548ABus(self, i) for i in range(8)]
        self.save = []

    def select_downstream(self, bus) -> None:
        if bus is not None and bus >= 0 and bus <=7 and self.cur_i2c_bus != bus:
            self.system_i2c.writeto(self.addr,bytes([(0x1<<bus)]))
            self.cur_i2c_bus=bus
        elif self.cur_i2c_bus != None:
            self.system_i2c.writeto(self.addr,bytes([0]))
            self.cur_i2c_bus=bus

    def save_downstream(self):
        self.save.append(self.cur_i2c_bus)

    def restore_downstream(self):
        self.select_downstream(self.save.pop())

    def get_downstream_bus(self, bus):
        return self.downstreams[bus]