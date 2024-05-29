from machine import Pin, I2C, SPI
import neopixel
import gc9a01py as gc9a01

BUS_SYSTEM = 7
BUS_TOP = 0
EPIN_LED_POWER = (0x5A, 0, (1 << 2))
EPIN_ND_A = (0x5A, 1, (1 << 4))
EPIN_ND_B = (0x5A, 1, (1 << 5))
EPIN_ND_C = (0x59, 1, (1 << 0))
EPIN_ND_D = (0x59, 1, (1 << 1))
EPIN_ND_E = (0x59, 1, (1 << 2))
EPIN_ND_F = (0x59, 1, (1 << 3))
led_colours = [
    (255, 0, 0),
    (255, 255, 0),
    (0, 255, 0),
    (0, 255, 255),
    (0, 0, 255),
    (255, 0, 255),
]

HEXPANSION_GPIOS = {
    "1_LS_A": (0x5A, 0, 1 << 3),
    "1_LS_B": (0x5A, 1, 1 << 0),
    "1_LS_C": (0x5A, 1, 1 << 1),
    "1_LS_D": (0x5A, 1, 1 << 2),
    "1_LS_E": (0x5A, 1, 1 << 3),
    "2_LS_A": (0x5A, 0, 1 << 0),
    "2_LS_B": (0x5A, 0, 1 << 1),
    "2_LS_C": (0x59, 1, 1 << 5),
    "2_LS_D": (0x59, 1, 1 << 6),
    "2_LS_E": (0x59, 1, 1 << 7),
    "3_LS_A": (0x59, 0, 1 << 4),
    "3_LS_B": (0x59, 0, 1 << 5),
    "3_LS_C": (0x59, 0, 1 << 6),
    "3_LS_D": (0x59, 0, 1 << 7),
    "3_LS_E": (0x59, 1, 1 << 4),
    "4_LS_A": (0x58, 1, 1 << 0),
    "4_LS_B": (0x58, 1, 1 << 1),
    "4_LS_C": (0x58, 1, 1 << 2),
    "4_LS_D": (0x58, 1, 1 << 3),
    "4_LS_E": (0x58, 0, 1 << 0),
    "5_LS_A": (0x58, 0, 1 << 2),
    "5_LS_B": (0x58, 0, 1 << 3),
    "5_LS_C": (0x58, 0, 1 << 4),
    "5_LS_D": (0x58, 0, 1 << 5),
    "5_LS_E": (0x58, 1, 1 << 6),
    "6_LS_A": (0x58, 0, 1 << 7),
    "6_LS_B": (0x58, 1, 1 << 4),
    "6_LS_C": (0x58, 1, 1 << 5),
    "6_LS_D": (0x58, 1, 1 << 6),
    "6_LS_E": (0x58, 1, 1 << 7),
}


class ExtendedPin:
    def __init__(self, pin_name, mode=-1):
        self.name = pin_name
        self.pin = HEXPANSION_GPIOS[pin_name]
        self.mode = mode

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)

    def value(self, value=None, read=True):
        if self.mode in (Pin.IN, -1) and value is None:
            return tildagonos.check_egpio_state(self.pin, readgpios=read)
        elif self.mode in (Pin.OUT, -1):
            return tildagonos.set_egpio_pin(self.pin, value)
        else:
            raise ValueError("Wrong pin state")


class _tildagonos:
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
        self.tft = gc9a01.GC9A01(
            self.spi, dc=Pin(2, Pin.OUT), cs=Pin(1, Pin.OUT), rotation=2
        )
        self.tft.fill(gc9a01.MAGENTA)

    def init_gpio(self):
        # egpio reset
        self.system_i2c.writeto_mem(0x58, 0x7F, bytes([0x00]))
        self.system_i2c.writeto_mem(0x59, 0x7F, bytes([0x00]))
        self.system_i2c.writeto_mem(0x5A, 0x7F, bytes([0x00]))
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

    def set_egpio_pin(self, pin, state):
        portstates = list(map(int, self.system_i2c.readfrom_mem(pin[0], 0x02, 2)))
        if state:
            self.system_i2c.writeto_mem(
                0x5A, 0x02 + pin[1], bytes([portstates[pin[1]] | pin[2]])
            )
        else:
            self.system_i2c.writeto_mem(
                0x5A, 0x02 + pin[1], bytes([portstates[pin[1]] & (pin[2] ^ 0xFF)])
            )

    def read_egpios(self):
        for i in [0x58, 0x59, 0x5A]:
            portstates = list(map(int, self.system_i2c.readfrom_mem(i, 0x00, 2)))
            self.gpiodata[i] = tuple(portstates)

    def check_egpio_state(self, pin, readgpios=True):
        if pin[0] not in self.gpiodata or readgpios:
            self.read_egpios()
        return bool(pin[2] & self.gpiodata[pin[0]][pin[1]])

    def set_led_power(self, state):
        self.set_egpio_pin(EPIN_LED_POWER, state)


tildagonos = _tildagonos()
