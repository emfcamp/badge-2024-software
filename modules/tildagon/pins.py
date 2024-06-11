import machine
from tildagonos import tildagonos

HEXPANSION_GPIOS = {
    "1_LS_A": (2, 3),
    "1_LS_B": (2, 8),
    "1_LS_C": (2, 9),
    "1_LS_D": (2, 10),
    "1_LS_E": (2, 11),
    "2_LS_A": (2, 0),
    "2_LS_B": (2, 1),
    "2_LS_C": (1, 13),
    "2_LS_D": (1, 14),
    "2_LS_E": (1, 15),
    "3_LS_A": (1, 4),
    "3_LS_B": (1, 5),
    "3_LS_C": (1, 6),
    "3_LS_D": (1, 7),
    "3_LS_E": (1, 12),
    "4_LS_A": (0, 8),
    "4_LS_B": (0, 9),
    "4_LS_C": (0, 10),
    "4_LS_D": (0, 11),
    "4_LS_E": (0, 0),
    "5_LS_A": (0, 2),
    "5_LS_B": (0, 3),
    "5_LS_C": (0, 4),
    "5_LS_D": (0, 5),
    "5_LS_E": (0, 14),
    "6_LS_A": (0, 7),
    "6_LS_B": (0, 12),
    "6_LS_C": (0, 13),
    "6_LS_D": (0, 14),
    "6_LS_E": (0, 15),
}


class Pin:
    def __init__(self, pin_name, mode=-1):
        self.name = pin_name
        self.pin = HEXPANSION_GPIOS[pin_name]
        self.mode = mode
        if self.mode in (machine.Pin.IN, -1):
            tildagonos.set_pin_mode(self.pin, machine.Pin.IN)
        elif self.mode == machine.Pin.OUT:
            tildagonos.set_pin_mode(self.pin, machine.Pin.OUT)
        else:
            raise ValueError("Invalid pin mode")

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
