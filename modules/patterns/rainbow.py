from patterns.base import BasePattern


class RainbowPattern(BasePattern):
    def __init__(self):
        super().__init__()
        self._current_frame_id = 0
        self.fps = 30
        num_pixels = 12
        num_frames = 60
        self.frames = []
        for j in range(num_frames):
            current_row = []
            for i in range(num_pixels):
                rc_index = ((i * 256 // num_pixels) + int(j * (255 / num_frames))) & 255
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
