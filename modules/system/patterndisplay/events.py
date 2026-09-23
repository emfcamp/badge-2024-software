from events import Event


class PatternEnable(Event): ...


class PatternDisable(Event): ...


class PatternReload(Event): ...


class PatternSet(Event):
    def __init__(self, pattern_class):
        self.pattern_class = pattern_class


class PatternOverride(Event):
    def __init__(self, led, new_value):
        self.led = led
        self.new_value = new_value


class PatternClearOverride(Event):
    def __init__(self, led):
        self.led = led
