import machine
from tildagonos import tildagonos




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


class Pin:
    def __init__(self, pin_name, mode=-1):
        self.name = pin_name
        self.pin = HEXPANSION_GPIOS[pin_name]
        self.mode = mode

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)

    def value(self, value=None, read=True):
        if self.mode in (machine.Pin.IN, -1) and value is None:
            return tildagonos.check_egpio_state(self.pin, readgpios=read)
        elif self.mode in (machine.Pin.OUT, -1):
            return tildagonos.set_egpio_pin(self.pin, value)
        else:
            raise ValueError("Wrong pin state")
