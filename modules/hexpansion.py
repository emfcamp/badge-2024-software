from tildagon import Pin as ls_pin
from machine import Pin as hs_pin


class hexpansion:
    OUT = ls_pin.OUT
    IN = ls_pin.IN
    PWM = ls_pin.PWM

    def __init__(self, port):
        pins = [
            {
                "LS_A": (2, 3),
                "LS_B": (2, 8),
                "LS_C": (2, 9),
                "LS_D": (2, 10),
                "LS_E": (2, 11),
                "HS_A": 39,
                "HS_B": 40,
                "HS_C": 41,
                "HS_D": 42,
            },
            {
                "LS_A": (2, 0),
                "LS_B": (2, 1),
                "LS_C": (1, 13),
                "LS_D": (1, 14),
                "LS_E": (1, 15),
                "HS_A": 35,
                "HS_B": 36,
                "HS_C": 37,
                "HS_D": 38,
            },
            {
                "LS_A": (1, 4),
                "LS_B": (1, 5),
                "LS_C": (1, 6),
                "LS_D": (1, 7),
                "LS_E": (1, 12),
                "HS_A": 34,
                "HS_B": 33,
                "HS_C": 47,
                "HS_D": 48,
            },
            {
                "LS_A": (0, 8),
                "LS_B": (0, 9),
                "LS_C": (0, 10),
                "LS_D": (0, 11),
                "LS_E": (0, 0),
                "HS_A": 11,
                "HS_B": 14,
                "HS_C": 13,
                "HS_D": 12,
            },
            {
                "LS_A": (0, 2),
                "LS_B": (0, 3),
                "LS_C": (0, 4),
                "LS_D": (0, 5),
                "LS_E": (0, 14),
                "HS_A": 18,
                "HS_B": 16,
                "HS_C": 15,
                "HS_D": 17,
            },
            {
                "LS_A": (0, 7),
                "LS_B": (0, 12),
                "LS_C": (0, 13),
                "LS_D": (0, 14),
                "LS_E": (0, 15),
                "HS_A": 3,
                "HS_B": 4,
                "HS_C": 5,
                "HS_D": 6,
            },
        ]
        self.ls_info = {
            "A": pins[port]["LS_A"],
            "B": pins[port]["LS_B"],
            "C": pins[port]["LS_C"],
            "D": pins[port]["LS_D"],
            "E": pins[port]["LS_E"],
        }
        self.hs_info = {
            "A": pins[port]["HS_A"],
            "B": pins[port]["HS_B"],
            "C": pins[port]["HS_C"],
            "D": pins[port]["HS_D"],
        }
        self.ls = {"A": None, "B": None, "C": None, "D": None, "E": None}
        self.hs = {"A": None, "B": None, "C": None, "D": None}
        for key in self.ls_info:
            self.ls[key] = ls_pin(self.ls_info[key], self.IN)
        for key in self.hs_info:
            self.hs[key] = hs_pin(self.hs_info[key], hs_pin.IN)


# example
# from hexpansion import hexpansion
# rabbit = hexpansion(3)
# red_eye = rabbit.ls["E"]
# red_eye.init(rabbit.OUT)
# red_eye.off()
# red_eye.on()
# red_eye.init(rabbit.PWM)
# red_eye.pwm(100)
# from machine import SPI
# hex_spi = SPI(1, 40000000, sck=rabbit.hs["A"], mosi=rabbit.hs["B"])
