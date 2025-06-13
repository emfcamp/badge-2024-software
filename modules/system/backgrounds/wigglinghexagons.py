from firmware_apps.intro_app import Hexagon
from app_components import clear_background


class WigglingHexagons:
    def __init__(self):
        self.wiggling_hexagons = [Hexagon() for _ in range(6)]
        self.time_elapsed = 0

    def update(self, delta):
        self.time_elapsed += delta / 1_000
        for hexagon in self.wiggling_hexagons:
            hexagon.update(self.time_elapsed)

    def draw(self, ctx):
        clear_background(ctx)
        for hexagon in self.wiggling_hexagons:
            hexagon.draw(ctx)


__Background__ = WigglingHexagons
