from patterns.base import BasePattern


class CylonPattern(BasePattern):
    def __init__(self, num_leds=12):
        super().__init__()
        self.fps = 11
        # the extra frames after the start of the wave gets to the end.
        # Some of these will be fade-out frames and, if there are enough, some pure black
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

        for i in range(self.num_leds + min(self.gap_frames, len(fall_off) - 1)):
            #first frame is a single bright first pixel, until the last pixel is bright then finally all are dark
            start = self.num_leds + len(fall_off) - i - 1
            frame = space[start : start + self.num_leds]
            frames.append(frame)
        #pure black frames if needed
        for i in range(self.gap_frames - len(fall_off)):
            frames.append([(0, 0, 0)] * self.num_leds)

        for i in range(self.num_leds + min(self.gap_frames, len(fall_off) - 1)):
            start = self.num_leds + len(fall_off) - i - 1
            # slice then reverse as a[1,2] is not the reverse of a[2:1:-1]
            frame = space[start : start + self.num_leds][::-1]
            frames.append(frame)
        for i in range(self.gap_frames - len(fall_off)):
            frames.append([(0, 0, 0)] * self.num_leds)

        self.frames = frames
