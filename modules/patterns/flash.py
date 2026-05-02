from patterns.base import BasePattern


class FlashPattern(BasePattern):
    def __init__(self, num_leds=12):
        super().__init__()
        self.fps = 1
        self.frames = [
            [(0, 0, 0) if i % 2 else (255, 255, 255) for i in range(num_leds)],
            [(0, 0, 0) if not i % 2 else (255, 255, 255) for i in range(num_leds)],
        ]
