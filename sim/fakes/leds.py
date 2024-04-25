from _sim import _sim
from sys_colors import hsv_to_rgb
from math import tau

import pygame


def set_rgb(ix, r, g, b):
    if r > 1:
        r /= 255
    if g > 1:
        g /= 255
    if b > 1:
        b /= 255
    r = min(1.0, max(0.0, r))
    g = min(1.0, max(0.0, g))
    b = min(1.0, max(0.0, b))
    _sim.set_led_rgb(ix, pow(r, 1 / 2.2), pow(g, 1 / 2.2), pow(b, 1 / 2.2))


def get_rgb(ix):
    return 0, 0, 0


def get_steady():
    return False


def set_all_rgb(r, g, b):
    for i in range(len(_sim.LED_POSITIONS)):
        set_rgb(i, r, g, b)


def set_hsv(ix, h, s, v):
    set_rgb(ix, *hsv_to_rgb(h / 360 * tau, s, v))


def set_all_hsv(h, s, v):
    for i in range(40):
        set_hsv(i, h, s, v)


def set_slew_rate(b: int):
    pass  # Better a no-op than not implemented at all.


def get_slew_rate():
    return 255


def update():
    _sim.leds_update()
    pygame.event.post(pygame.event.Event(pygame.USEREVENT, {}))


def set_auto_update(b: int):
    pass


def set_brightness(b: float):
    pass


def set_gamma(r: float, g: float, b: float):
    pass
