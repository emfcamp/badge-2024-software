from machine import Pin, I2C, SPI
import neopixel
import gc9a01py as gc9a01
import tildagon

BUS_SYSTEM = 7
BUS_TOP = 0
EPIN_LED_POWER = (2, 2)
EPIN_ND_A = (2, 12)
EPIN_ND_B = (2, 13)
EPIN_ND_C = (1, 8)
EPIN_ND_D = (1, 9)
EPIN_ND_E = (1, 10)
EPIN_ND_F = (1, 11)
led_colours = [
    (255, 0, 0),
    (255, 255, 0),
    (0, 255, 0),
    (0, 255, 255),
    (0, 0, 255),
    (255, 0, 255),
]


class _tildagonos:
    def __init__(self):
        self.system_i2c = I2C(7)
        self.init_gpio()
        self.leds = neopixel.NeoPixel(Pin(21), 19)
        self.gpiodata = {}
        self.spi = None
        self.tft = None

    def init_display(self):
        self.spi = SPI(1, 40000000, sck=Pin(8), mosi=Pin(7))
        self.tft = gc9a01.GC9A01(
            self.spi, dc=Pin(2, Pin.OUT), cs=Pin(1, Pin.OUT), rotation=2
        )
        self.tft.fill(gc9a01.MAGENTA)

    def init_gpio(self):
        # egpio reset
        # self.system_i2c.writeto_mem(0x58, 0x7F, bytes([0x00]))
        # self.system_i2c.writeto_mem(0x59, 0x7F, bytes([0x00]))
        # self.system_i2c.writeto_mem(0x5A, 0x7F, bytes([0x00]))
        # chip A - disable interrupts
        self.system_i2c.writeto_mem(0x58, 0x06, bytes([0xFF, 0xFF]))
        # chip A - set everything to input
        self.system_i2c.writeto_mem(0x58, 0x04, bytes([0xFF, 0xFF]))
        # chip A - switch mode to push-pull
        self.system_i2c.writeto_mem(0x58, 0x11, bytes([0x10]))

        # chip B - disable interrupts
        self.system_i2c.writeto_mem(0x59, 0x06, bytes([0xFF, 0xFF]))
        # chip B - set everything to input
        self.system_i2c.writeto_mem(0x59, 0x04, bytes([0xFF, 0xFF]))
        # chip B - switch mode to push-pull
        self.system_i2c.writeto_mem(0x59, 0x11, bytes([0x10]))
        # chip C - disable interrupts
        self.system_i2c.writeto_mem(0x5A, 0x06, bytes([0xFF, 0xFF]))
        # chip C - set P0 bits 0,1,3,6,7 and P1 bits 0,1,2,3,4,5,6,7 to input
        self.system_i2c.writeto_mem(0x5A, 0x04, bytes([0xCB, 0xFF]))
        # chip C - set P0_4(PMID_SW) to 0, set P0_5(USBSEL) to 0, set P0_2(led_power_en) to 0
        self.system_i2c.writeto_mem(0x5A, 0x02, bytes([0x00]))
        # chip C - switch mode to push-pull
        self.system_i2c.writeto_mem(0x5A, 0x11, bytes([0x10]))

        for pin in [(2, 2), (2, 4), (2, 5)]:
            tildagon.Pin(pin).init(tildagon.Pin.OUT)

    def set_egpio_pin(self, pin, state):
        pin = self.convert_pin(pin)
        pin = tildagon.Pin(pin)
        pin(state)

    @staticmethod
    def convert_pin(pin):
        if len(pin) == 3:
            bitpos = 0
            while pin[2] & (1 << bitpos) == 0:
                bitpos += 1
            pin = (pin[0] - 0x58, pin[1] * 8 + bitpos)
        return pin

    def read_egpios(self):
        for i in [0x58, 0x59, 0x5A]:
            self.gpiodata[i] = (
                self.system_i2c.readfrom_mem(i, 0, 1)[0],
                self.system_i2c.readfrom_mem(i, 1, 1)[0],
            )

    def check_egpio_state(self, pin, readgpios=True):
        pin = self.convert_pin(pin)
        pin = tildagon.Pin(pin)
        return pin()

    def set_led_power(self, state):
        self.set_egpio_pin(EPIN_LED_POWER, state)


tildagonos = _tildagonos()
