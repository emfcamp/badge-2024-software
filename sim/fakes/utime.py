import time


def sleep(i: int):
    time.sleep(i)

def ticks_ms():
    return time.monotonic()
