from machine import Pin, SPI
import neopixel
from egpio import ePin

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
        self.spi = None
        self.tft = None

    def init_gpio(self):
        print(
            "Warning init_gpio has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )

    @staticmethod
    def convert_pin(pin):
        if len(pin) == 3:
            bitpos = 0
            while pin[2] & (1 << bitpos) == 0:
                bitpos += 1
            pin = (pin[0] - 0x58, pin[1] * 8 + bitpos)
        return pin

    def set_pin_mode(self, pin, mode=Pin.IN):
        print(
            "Warning set_pin_mode has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )
        pin = self.convert_pin(pin)
        pin = ePin(pin)
        if mode == Pin.IN or mode == Pin.OUT or mode == ePin.PWM:
            pin.init(mode)
        else:
            raise ValueError("Invalid pin mode")

    def set_egpio_pin(self, pin, state):
        """
        Write an output state to a specific pin on a GPIO expander

        @param pin: tuple of (i2c addr, port number 0/1, bitmask) or (device 0-2, pin 0-15) selecting the pin to modify
        @param state: True to set the pin high, False to set the pin low
        """
        print(
            "Warning set_egpio_pin has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )
        pin = self.convert_pin(pin)
        pin = ePin(pin)
        pin(state)

    def read_egpios(self):
        print(
            "Warning read_egpios has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )

    def check_egpio_state(self, pin, readgpios=True):
        print(
            "Warning check_egpio_state has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )
        pin = self.convert_pin(pin)
        pin = ePin(pin)
        return pin()

    def set_led_power(self, state):
        ePin(EPIN_LED_POWER)(state)


tildagonos = _tildagonos()
