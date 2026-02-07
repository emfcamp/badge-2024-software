from events import Event


class PatternEnable(Event): ...


class PatternDisable(Event): ...


class PatternReload(Event): ...


class PatternSet(Event):
    def __init__(self, pattern_class):
        self.pattern_class = pattern_class
