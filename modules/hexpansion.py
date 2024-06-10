from tildagon import Pin as ls_pin
from machine import Pin as hs_pin


class port:
    OUT = ls_pin.OUT
    IN = ls_pin.IN
    PWM = ls_pin.PWM

    def __init__(self, LS_A, LS_B, LS_C, LS_D, LS_E, HS_A, HS_B, HS_C, HS_D):
        self.ls_info = {"A": LS_A, "B": LS_B, "C": LS_C, "D": LS_D, "E": LS_E}
        self.hs_info = {"A": HS_A, "B": HS_B, "C": HS_C, "D": HS_D}
        self.ls = {"A": None, "B": None, "C": None, "D": None, "E": None}
        self.hs = {"A": None, "B": None, "C": None, "D": None}
        for key in self.ls_info:
            self.ls[key] = ls_pin(self.ls_info[key], self.IN)
        for key in self.hs_info:
            self.hs[key] = hs_pin(self.hs_info[key], hs_pin.IN)


hexpansion = [
    port((2, 3), (2, 8), (2, 9), (2, 10), (2, 11), 39, 40, 41, 42),
    port((2, 0), (2, 1), (1, 13), (1, 14), (1, 15), 35, 36, 37, 38),
    port((1, 4), (1, 5), (1, 6), (1, 7), (1, 12), 34, 33, 47, 48),
    port((0, 8), (0, 9), (0, 10), (0, 11), (0, 0), 11, 14, 13, 12),
    port((0, 2), (0, 3), (0, 4), (0, 5), (0, 14), 18, 16, 15, 17),
    port((0, 7), (0, 12), (0, 13), (0, 14), (0, 15), 3, 4, 5, 6),
]

# example
# from hexpansion import hexpansion
# rabbit = hexpansion[3]
# red_eye = rabbit.ls["E"]
# red_eye.init(rabbit.OUT)
# red_eye.off()
# red_eye.on()
# red_eye.init(rabbit.PWM)
# red_eye.pwm(100)
# from machine import SPI
# hex_spi = SPI(1, 40000000, sck=hexpansion[1].hs["A"], mosi=hexpansion[1].hs["B"])
