import settings

from app import App
from system.eventbus import eventbus
from system.hexpansion.events import HexpansionInsertionEvent, HexpansionRemovalEvent
from tildagonos import tildagonos, led_colours

# note that event.port is indexed from 1-6,
# hexpansion style, but this list is indexed from 0-5,
# Python style.
active_back_leds = [False] * 6


class BackLEDManager(App):
    def __init__(self):
        tildagonos.set_led_power(True)
        eventbus.on_async(HexpansionInsertionEvent, self.handle_insertion, self)
        eventbus.on_async(HexpansionRemovalEvent, self.handle_removal, self)

    async def handle_insertion(self, event):
        active_back_leds[event.port - 1] = True

    async def handle_removal(self, event):
        active_back_leds[event.port - 1] = False

    def background_update(self, delta):
        for i in range(0, 6):
            if active_back_leds[i]:
                if settings.get("pattern_mirror_hexpansions", False):
                    tildagonos.leds[13 + i] = tildagonos.leds[1 + (i * 2)]
                else:
                    tildagonos.leds[13 + i] = led_colours[i]
            else:
                tildagonos.leds[13 + i] = (0, 0, 0)
        tildagonos.leds.write()
