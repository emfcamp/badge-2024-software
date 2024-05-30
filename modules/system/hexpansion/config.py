from machine import Pin, I2C
from tildagon import Pin as ePin

_pin_mapping = {
    1: {
        "hs": [39, 40, 41, 42],
        "ls": ["1_LS_A", "1_LS_B", "1_LS_C", "1_LS_D", "1_LS_E"],
    },
    2: {
        "hs": [35, 36, 37, 38],
        "ls": ["2_LS_A", "2_LS_B", "2_LS_C", "2_LS_D", "2_LS_E"],
    },
    3: {
        "hs": [34, 33, 47, 48],
        "ls": ["3_LS_A", "3_LS_B", "3_LS_C", "3_LS_D", "3_LS_E"],
    },
    4: {
        "hs": [11, 14, 13, 12],
        "ls": ["4_LS_A", "4_LS_B", "4_LS_C", "4_LS_D", "4_LS_E"],
    },
    5: {
        "hs": [18, 16, 15, 17],
        "ls": ["5_LS_A", "5_LS_B", "5_LS_C", "5_LS_D", "5_LS_E"],
    },
    6: {
        "hs": [3, 4, 5, 6],
        "ls": ["6_LS_A", "6_LS_B", "6_LS_C", "6_LS_D", "6_LS_E"],
    },
}


# TODO: come up with a better name for this?
class HexpansionConfig:
    def __init__(self, port):
        self.port = port
        self.pin = [Pin(x) for x in _pin_mapping[port]["hs"]]
        self.ls_pin = [ePin(x) for x in _pin_mapping[port]["ls"]]
        self.i2c = I2C(port)
