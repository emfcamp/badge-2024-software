from machine import Pin, SPI
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
        self.leds = neopixel.NeoPixel(Pin(21), 19)
        # self.gpiodata = {}
        self.spi = None
        self.tft = None

    def init_display(self):
        self.spi = SPI(1, 40000000, sck=Pin(8), mosi=Pin(7))
        self.tft = gc9a01.GC9A01(
            self.spi, dc=Pin(2, Pin.OUT), cs=Pin(1, Pin.OUT), rotation=2
        )
        self.tft.fill(gc9a01.MAGENTA)

    def init_gpio(self): ...

    @staticmethod
    def convert_pin(pin):
        if len(pin) == 3:
            bitpos = 0
            while pin[2] & (1 << bitpos) == 0:
                bitpos += 1
            pin = (pin[0] - 0x58, pin[1] * 8 + bitpos)
        return pin

    def set_pin_mode(self, pin, mode=Pin.IN):
        portstates = list(map(int, self.system_i2c.readfrom_mem(pin[0], 0x04, 2)))
        if mode == Pin.IN:
            self.system_i2c.writeto_mem(
                pin[0], 0x04 + pin[1], bytes([portstates[pin[1]] | pin[2]])
            )
        elif mode == Pin.OUT:
            self.system_i2c.writeto_mem(
                pin[0], 0x04 + pin[1], bytes([portstates[pin[1]] & (pin[2] ^ 0xFF)])
            )
        else:
            raise ValueError("Invalid pin mode")

    def set_egpio_pin(self, pin, state):
        """
        Write an output state to a specific pin on a GPIO expander

        @param pin: tuple of (i2c addr, port number 0/1, bitmask) selecting the pin to modify
        @param state: True to set the pin high, False to set the pin low
        """
        pin = self.convert_pin(pin)
        pin = tildagon.Pin(pin)
        pin(state)

    def read_egpios(self):
        ...
        # for i in [0x58, 0x59, 0x5A]:
        #    portstates = list(map(int, self.system_i2c.readfrom_mem(i, 0x00, 2)))
        #    self.gpiodata[i] = tuple(portstates)

    def check_egpio_state(self, pin, readgpios=True):
        pin = self.convert_pin(pin)
        pin = tildagon.Pin(pin)
        return pin()

    def set_led_power(self, state):
        tildagon.Pin(EPIN_LED_POWER)(state)


tildagonos = _tildagonos()
