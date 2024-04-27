from typing import Tuple
import pygame
from math import tau


def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[float, float, float]:
    color = pygame.Color(0)
    color.hsva = ((h % tau) / tau * 360, s * 100, v * 100, 100)
    return color.normalize()[:3]


def rgb_to_hsv(r: float, g: float, b: float) -> Tuple[float, float, float]:
    color = pygame.Color(int(r * 255), int(g * 255), int(b * 255))
    h, s, v, a = color.hsva
    return (h / 360 * tau, s / 100, v / 100)
