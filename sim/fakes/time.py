import importlib
import pygame

_time = importlib.import_module("_time")


def sleep_ms(ms):
    _time.sleep(ms * 0.001)


def ticks_ms():
    return int(_time.time() * 1000)

def ticks_us():
    return int(_time.time() * 1000000)

def ticks_diff(a, b):
    return a - b


def ticks_add(a, b):
    return a + b
