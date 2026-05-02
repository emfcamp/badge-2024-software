from patterns.base import BasePattern


class OffPattern(BasePattern):
    def __init__(self, num_leds=12):
        super().__init__()
        self.fps = 1
        self.frames = [[(0, 0, 0)] * self.num_leds]
