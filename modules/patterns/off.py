from patterns.base import BasePattern


class OffPattern(BasePattern):
    def __init__(self):
        super().__init__()
        self.fps = 1
        self.frames = [[(0, 0, 0)] * 12]
