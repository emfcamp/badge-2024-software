from patterns.base import BasePattern


class CylonPattern(BasePattern):
    def __init__(self, num_leds=12):
        super().__init__()
        self.fps = 11
        self.gap_frames = 9
        self.num_leds = num_leds
        self.make_frames()

    def make_frames(self):
        self.frames = []
        fall_off = [
            (1, 0, 0),
            (2, 0, 0),
            (4, 0, 0),
            (8, 0, 0),
            (15, 0, 0),
            (31, 0, 0),
            (63, 0, 0),
            (127, 0, 0),
            (255, 0, 0),
        ]

        space = ([(0, 0, 0)] * self.num_leds) + fall_off + ([(0, 0, 0)] * self.num_leds)

        frames = []

        for i in range(self.num_leds):
            frame = space[8 + self.num_leds - i : 8 + self.num_leds + self.num_leds - i]
            frames.append(frame)
        for i in range(self.gap_frames):
            frames.append([(0, 0, 0)] * self.num_leds)
        for i in range(self.num_leds):
            frame = space[
                8 + self.num_leds + self.num_leds - i : 8 + self.num_leds - i : -1
            ]
            frames.append(frame)
        for i in range(self.gap_frames):
            frames.append([(0, 0, 0)] * self.num_leds)

        self.frames = frames
