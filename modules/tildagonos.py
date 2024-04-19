from machine import Pin, I2C, SPI
from perf_timer import PerfTimer
import neopixel, time
import gc9a01py as gc9a01
import asyncio

BUS_SYSTEM = 7
BUS_TOP = 0
EPIN_LED_POWER = (0x5a, 0, (1 << 2))
EPIN_ND_A = (0x5a, 1, (1 << 4))
EPIN_ND_B = (0x5a, 1, (1 << 5))
EPIN_ND_C = (0x59, 1, (1 << 0))
EPIN_ND_D = (0x59, 1, (1 << 1))
EPIN_ND_E = (0x59, 1, (1 << 2))
EPIN_ND_F = (0x59, 1, (1 << 3))
EPIN_BTN_1 = (0x5a, 0, (1 << 6))
EPIN_BTN_2 = (0x5a, 0, (1 << 7))
EPIN_BTN_3 = (0x59, 0, (1 << 0))
EPIN_BTN_4 = (0x59, 0, (1 << 1))
EPIN_BTN_5 = (0x59, 0, (1 << 2))
EPIN_BTN_6 = (0x59, 0, (1 << 3))
led_colours = [
    (255, 0, 0),
    (255, 255, 0),
    (0, 255, 0),
    (0, 255, 255),
    (0, 0, 255),
    (255, 0, 255),
]


class tildagonos:

    def __init__(self):
        self.pin_reset_i2c = Pin(9, Pin.OUT)
        self.pin_reset_i2c.on()
        self.system_i2c = I2C(7)
        self.init_gpio()
        self.leds = neopixel.NeoPixel(Pin(21), 19)
        self.gpiodata = {}
        self.spi = None
        self.tft = None

    def init_display(self):
        self.spi = SPI(1, 40000000, sck=Pin(8), mosi=Pin(7))
        self.tft = gc9a01.GC9A01(self.spi, dc=Pin(2, Pin.OUT), cs=Pin(1, Pin.OUT), rotation=2)
        self.tft.fill(gc9a01.MAGENTA)

    def init_gpio(self):
        # egpio reset
        self.system_i2c.writeto_mem(0x58, 0x7f, bytes([0x00]))
        self.system_i2c.writeto_mem(0x59, 0x7f, bytes([0x00]))
        self.system_i2c.writeto_mem(0x5a, 0x7f, bytes([0x00]))
        # chip A - disable interrupts
        self.system_i2c.writeto_mem(0x58, 0x06, bytes([0xff, 0xff]))
        # chip A - set everything to input
        self.system_i2c.writeto_mem(0x58, 0x04, bytes([0xff, 0xff]))
        # chip A - switch mode to push-pull
        self.system_i2c.writeto_mem(0x58, 0x11, bytes([0x10]))

        # chip B - disable interrupts
        self.system_i2c.writeto_mem(0x59, 0x06, bytes([0xff, 0xff]))
        # chip B - set everything to input
        self.system_i2c.writeto_mem(0x59, 0x04, bytes([0xff, 0xff]))
        # chip B - switch mode to push-pull
        self.system_i2c.writeto_mem(0x59, 0x11, bytes([0x10]))
        # chip C - disable interrupts
        self.system_i2c.writeto_mem(0x5a, 0x06, bytes([0xff, 0xff]))
        # chip C - set P0 bits 0,1,3,6,7 and P1 bits 0,1,2,3,4,5,6,7 to input
        self.system_i2c.writeto_mem(0x5a, 0x04, bytes([0xcb, 0xff]))
        # chip C - set P0_4(PMID_SW) to 0, set P0_5(USBSEL) to 0, set P0_2(led_power_en) to 0
        self.system_i2c.writeto_mem(0x5a, 0x02, bytes([0x00]))
        # chip C - switch mode to push-pull
        self.system_i2c.writeto_mem(0x5a, 0x11, bytes([0x10]))

    def set_egpio_pin(self, pin, state):
        portstates = list(map(int, self.system_i2c.readfrom_mem(pin[0], 0x02, 2)))
        if state:
            self.system_i2c.writeto_mem(0x5a, 0x02 + pin[1], bytes([portstates[pin[1]] | pin[2]]))
        else:
            self.system_i2c.writeto_mem(0x5a, 0x02 + pin[1], bytes([portstates[pin[1]] & (pin[2] ^ 0xff)]))

    def read_egpios(self):
        for i in [0x58, 0x59, 0x5a]:
            portstates = list(map(int, self.system_i2c.readfrom_mem(i, 0x00, 2)))
            self.gpiodata[i] = tuple(portstates)

    def check_egpio_state(self, pin, readgpios=True):
        if not pin[0] in self.gpiodata or readgpios:
            self.read_egpios()
        return bool(pin[2] & self.gpiodata[pin[0]][pin[1]])

    def set_led_power(self, state):
        self.set_egpio_pin(EPIN_LED_POWER, state)

    async def indicate_hexpansion_insertion(self):
        self.set_led_power(True)
        while True:
            with PerfTimer("indicate hexpansion insertion"):
                self.read_egpios()
                self.leds.fill((0, 0, 0))
                for i, n in enumerate([EPIN_ND_A, EPIN_ND_B, EPIN_ND_C, EPIN_ND_D, EPIN_ND_E, EPIN_ND_F]):
                    if not self.check_egpio_state(n):
                        self.leds[13 + i] = led_colours[i]
                for i, n in enumerate([EPIN_BTN_1, EPIN_BTN_2, EPIN_BTN_3, EPIN_BTN_4, EPIN_BTN_5, EPIN_BTN_6]):
                    if not self.check_egpio_state(n):
                        if i:
                            self.leds[i * 2] = led_colours[i]
                        else:
                            self.leds[12] = led_colours[i]
                        self.leds[1 + i * 2] = led_colours[i]
                self.leds.write()
            await asyncio.sleep(0.1)
