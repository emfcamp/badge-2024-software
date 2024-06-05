from events import Event
import settings
from tildagonos import tildagonos
from tildagonos import led_colours


class HexpansionEvent(Event):
    def __init__(self, port):
        self.port = port


class HexpansionInsertionEvent(HexpansionEvent):
    def __str__(self):
        if settings.get("pattern_mirror_hexpansions", False):
            tildagonos.leds[13 + self.port - 1] = tildagonos.leds[
                1 + ((self.port - 1) * 2)
            ]
        else:
            tildagonos.leds[13 + self.port - 1] = led_colours[self.port - 1]
        return f"Hexpansion inserted in port: {self.port}"


class HexpansionRemovalEvent(HexpansionEvent):
    def __str__(self):
        tildagonos.leds[13 + self.port - 1] = (0, 0, 0)
        return f"Hexpansion removed from port: {self.port}"


class HexpansionFormattedEvent(HexpansionEvent):
    def __str__(self):
        return f"Hexpansion in port {self.port} formatted"


class HexpansionMountedEvent(HexpansionEvent):
    def __str__(self):
        return f"Hexpansion in port {self.port} mounted"
