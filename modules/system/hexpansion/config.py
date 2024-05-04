from machine import Pin, I2C

_pin_mapping = {
    1: {
        "hs": [39, 40, 41, 42],
        "ls": [],  # TODO: need gpio extenders first
    },
    2: {
        "hs": [35, 36, 37, 38],
        "ls": [],  # TODO: need gpio extenders first
    },
    3: {
        "hs": [34, 33, 47, 48],
        "ls": [],  # TODO: need gpio extenders first
    },
    4: {
        "hs": [11, 14, 13, 12],
        "ls": [],  # TODO: need gpio extenders first
    },
    5: {
        "hs": [18, 16, 15, 17],
        "ls": [],  # TODO: need gpio extenders first
    },
    6: {
        "hs": [3, 4, 5, 6],
        "ls": [],  # TODO: need gpio extenders first
    }
}


# TODO: come up with a better name for this?
class HexpansionConfig:
    def __init__(self, port):
        self.pin = [Pin(x) for x in _pin_mapping[port]["hs"]]
        self.i2c = I2C(port)
