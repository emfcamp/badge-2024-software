from machine import Pin, I2C, SPI
import neopixel, time
import gc9a01py as gc9a01
from tca9548a import TCA9548A
from aw9523b import AW9523B, AW9523BPin

BUS_SYSTEM=7
BUS_TOP=0
EPIN_LED_POWER=(0x5a, 0, (1<<2))
EPIN_ND_A=(0x5a, 1, (1<<4))
EPIN_ND_B=(0x5a, 1, (1<<5))
EPIN_ND_C=(0x59, 1, (1<<0))
EPIN_ND_D=(0x59, 1, (1<<1))
EPIN_ND_E=(0x59, 1, (1<<2))
EPIN_ND_F=(0x59, 1, (1<<3))
EPIN_BTN_1=(0x5a, 0, (1<<6))
EPIN_BTN_2=(0x5a, 0, (1<<7))
EPIN_BTN_3=(0x59, 0, (1<<0))
EPIN_BTN_4=(0x59, 0, (1<<1))
EPIN_BTN_5=(0x59, 0, (1<<2))
EPIN_BTN_6=(0x59, 0, (1<<3))
led_colours=[
    (255, 0, 0),
    (255, 255, 0),
    (0, 255, 0),
    (0, 255, 255),
    (0, 0, 255),
    (255, 0, 255),    
]

class tildagonos:
    instance = None
    def __init__(self):
        self.pin_reset_i2c=Pin(9,Pin.OUT)
        self.pin_reset_i2c.on()
        self.system_i2c=I2C(0, scl=Pin(46), sda=Pin(45), freq=400000)
        self.i2c_expansion=TCA9548A(self.system_i2c, 0x77)
        self.init_gpio()
        self.leds=neopixel.NeoPixel(Pin(21),19)
        self.gpiodata={}
        self.spi=None
        self.tft=None
        self.pin_system_irq=Pin(10,Pin.IN)
        self.pin_system_irq.irq(self.system_irq_handler, Pin.IRQ_RISING)

        self.egpio_a = AW9523B(self.i2c_expansion.get_downstream_bus(BUS_SYSTEM), 0x58)
        self.egpio_b = AW9523B(self.i2c_expansion.get_downstream_bus(BUS_SYSTEM), 0x59)
        self.egpio_c = AW9523B(self.i2c_expansion.get_downstream_bus(BUS_SYSTEM), 0x5a)

        self.LED_POWER = AW9523BPin(self.egpio_a, (0, 2), mode=Pin.ALT)

        tildagonos.instance = self
        
    def init_display(self):
        self.spi=SPI(1,40000000, sck=Pin(8), mosi=Pin(7))
        self.tft=gc9a01.GC9A01(self.spi, dc=Pin(2, Pin.OUT), cs=Pin(1,Pin.OUT), rotation=2)
        self.tft.fill(gc9a01.MAGENTA)
        
    def init_gpio(self):
        self.i2c_expansion.save_downstream()
        sys_i2c = self.i2c_expansion.get_downstream_bus(BUS_SYSTEM)
        self.egpio_a.init()
        self.egpio_b.init()
        self.egpio_c.init()
        #I'd like this to not be direct access but it works as is.
        #chip C - set P0 bits 0,1,3,6,7 and P1 bits 0,1,2,3,4,5,6,7 to input
        sys_i2c.writeto_mem(0x5a, 0x04, bytes([0xcb,0xff]))
        #chip C - set P0_4(PMID_SW) to 0, set P0_5(USBSEL) to 0, set P0_2(led_power_en) to 0
        sys_i2c.writeto_mem(0x5a, 0x02, bytes([0x00]))
        self.i2c_expansion.restore_downstream()
        
    def set_egpio_pin(self, pin, state):
        self.i2c_expansion.save_downstream()
        egpios = [self.egpio_a, self.egpio_b, self.egpio_c]
        egpio = egpios[pin[0]-0x59]
        pinidx = 0
        v = pin[2]
        while (v := v//2):
            pinidx += 1
        egpio.pin_write((pin[1], pinidx), state)
        self.i2c_expansion.restore_downstream()
        
    def read_egpios(self):
        self.i2c_expansion.save_downstream()
        for eg in [self.egpio_a, self.egpio_b, self.egpio_c]:
            portstates=list(map(int,eg.bus.readfrom_mem(eg.addr,0x00,2)))
            self.gpiodata[eg.addr]=tuple(portstates)
        self.i2c_expansion.restore_downstream()
        
    def check_egpio_state(self, pin, readgpios=True):
        if not pin[0] in self.gpiodata or readgpios:
            self.read_egpios()
        return bool(pin[2]&self.gpiodata[pin[0]][pin[1]])
    
    def set_led_power(self, state):
        self.i2c_expansion.save_downstream()
        self.LED_POWER.value(state)
        self.i2c_expansion.restore_downstream()
        
    def indicate_hexpansion_insertion(self):
        self.set_led_power(True)
        while True:
            self.read_egpios()
            self.leds.fill((0,0,0))
            for i,n in enumerate([EPIN_ND_A,EPIN_ND_B,EPIN_ND_C,EPIN_ND_D,EPIN_ND_E,EPIN_ND_F]):
                if not self.check_egpio_state(n):
                    self.leds[13+i]=led_colours[i]
            for i,n in enumerate([EPIN_BTN_1,EPIN_BTN_2,EPIN_BTN_3,EPIN_BTN_4,EPIN_BTN_5,EPIN_BTN_6]):
                if not self.check_egpio_state(n):
                    if i:
                        self.leds[i*2]=led_colours[i]
                    else:
                       self.leds[12]=led_colours[i]
                    self.leds[1+i*2]=led_colours[i]
            self.leds.write()
            time.sleep(0.1)
            
    def sel_i2c_bus(self, bus=None):
        """
        TO BE DEPRACATED
        use the TCA9548 bus wrappper instead!
        """
        if bus is not None and bus >= 0 and bus <=7:
            self.system_i2c.writeto(0x77,bytes([(0x1<<bus)]))
            self.cur_i2c_bus=bus
        else:
            self.system_i2c.writeto(0x77,bytes([0]))
            self.cur_i2c_bus=None

    @staticmethod()
    def system_irq_handler(pin):
        # Add some interrupt handling code here?
        # probably good to micropython.schedule deferred stuff
        # that's not as urgent
        pass