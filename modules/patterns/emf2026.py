from patterns.palette import PalettePattern

class Emf2026Pattern(PalettePattern):
    def __init__(self, num_leds=12):
        #super().__init__(num_leds, [
        #    [0, 245, 81, 94], # coral
        #    [42, 247, 127, 2], # orange
        #    [84, 249, 226, 0], # yellow
        #    [126, 42, 226, 140], # green
        #    [168, 46, 173, 217], # light blue
        #    [210, 0, 93, 150], # mid blue
        #    # [218, 0, 7, 48], # dark blue #This is just "off" for the LEDs so don't bother with it.
        #], 120, 3)
        super().__init__(num_leds, [
            [0, 245, 81, 94], # coral
            [84, 247, 127, 2], # orange
            [168, 249, 226, 0], # yellow
        ], 60, 3)
