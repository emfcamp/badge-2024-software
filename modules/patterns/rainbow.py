from patterns.base import BasePattern


class RainbowPattern(BasePattern):
    def __init__(self, num_leds=12):
        super().__init__()
        self._current_frame_id = 0
        self.fps = 30
        self.num_pixels = num_leds
        self.num_frames = 60
        self.make_frames()

    def make_frames(self):
        self.frames = []
        for j in range(self.num_frames):
            current_row = []
            for i in range(self.num_pixels):
                rc_index = (
                    (i * 256 // self.num_pixels) + int(j * (255 / self.num_frames))
                ) & 255
                if rc_index < 0 or rc_index > 255:
                    current_row.append((0, 0, 0))
                elif rc_index < 85:
                    current_row.append((255 - rc_index * 3, rc_index * 3, 0))
                elif rc_index < 170:
                    rc_index -= 85
                    current_row.append((0, 255 - rc_index * 3, rc_index * 3))
                else:
                    rc_index -= 170
                    current_row.append((rc_index * 3, 0, 255 - rc_index * 3))
            self.frames.append(current_row)
