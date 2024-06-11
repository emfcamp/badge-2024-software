import os
import sys


class Pin:
    IN = None
    OUT = None

    def __init__(self, *args, **kwargs):
        pass

    def value(self):
        return 1

    def on(self):
        pass

    def off(self):
        pass


class ADC:
    ATTN_11DB = None

    def __init__(self, _1, atten):
        pass

    def read_uv(self):
        # A half full battery as seen by the ADC
        return 3.8e6 / 2


class I2C:
    def __init__(self, *args, **kwargs):
        pass

    def scan(self):
        return []

    def writeto(self, *args, **kwargs):
        return 0

    def writeto_mem(self, *args, **kwargs):
        return 0

    def readfrom_mem(self, *args, **kwargs):
        return b''


class SPI:
    pass

def reset():
    print("beep boop i have reset")
    os.execv(sys.executable, ["python"] + sys.argv)


def disk_mode_flash():
    print("beep boop i'm now in flash disk mode")
    sys.exit(0)


def disk_mode_sd():
    print("beep boop i'm now in sd card disk mode")
    sys.exit(0)
