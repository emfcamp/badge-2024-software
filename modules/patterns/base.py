class BasePattern:
    def __init__(self):
        self._current_frame_id = 0
        self.fps = 1
        self.frames = [[(255, 255, 255)] * 12]

    def next(self):
        self._current_frame_id += 1
        if self._current_frame_id == len(self.frames):
            self._current_frame_id = 0
        return self.frames[self._current_frame_id]

    def current(self):
        return self.frames[self._current_frame_id]
