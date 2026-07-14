import asyncio
import settings

from app import App
from events.emote import EmotePositiveEvent, EmoteNegativeEvent
from system.eventbus import eventbus
from system.hexpansion.events import HexpansionInsertionEvent, HexpansionRemovalEvent
from system.patterndisplay.events import PatternDisable, PatternEnable
from tildagonos import tildagonos, led_colours

# note that event.port is indexed from 1-6,
# hexpansion style, but this list is indexed from 0-5,
# Python style.
active_back_leds = [False] * 6


class BackLEDManager(App):
    def __init__(self):
        # routines that want to drive the back leds themselves for
        # a notification should take this lock.
        self.lock = asyncio.Lock()
        self.enabled = True
        tildagonos.set_led_power(True)
        eventbus.on_async(HexpansionInsertionEvent, self.handle_insertion, self)
        eventbus.on_async(HexpansionRemovalEvent, self.handle_removal, self)

        eventbus.on_async(EmotePositiveEvent, self.handle_positive, self)
        eventbus.on_async(EmoteNegativeEvent, self.handle_negative, self)

        eventbus.on_async(PatternDisable, self.handle_disable, self)
        eventbus.on_async(PatternEnable, self.handle_enable, self)

    async def handle_enable(self, event):
        self.enabled = True

    async def handle_disable(self, event):
        self.enabled = False

    async def handle_positive(self, event):
        if not self.enabled:
            return

        if not settings.get("backleds_emotes", True):
            return

        await self.lock.acquire()
        try:
            for brightness in [1, 16, 64, 255, 64, 16, 1, 0]:
                for lednum in range(13, 19):
                    tildagonos.leds[lednum] = (0, brightness, 0)
                tildagonos.leds.write()
                await asyncio.sleep(0.05)
        finally:
            self.lock.release()

    async def handle_negative(self, event):
        if not self.enabled:
            return

        if not settings.get("backleds_emotes", True):
            return

        await self.lock.acquire()
        try:
            for brightness in [1, 16, 64, 255, 64, 16, 1, 0]:
                for lednum in range(13, 19):
                    tildagonos.leds[lednum] = (brightness, 0, 0)
                tildagonos.leds.write()
                await asyncio.sleep(0.05)
        finally:
            self.lock.release()

    async def handle_insertion(self, event):
        active_back_leds[event.port - 1] = True

    async def handle_removal(self, event):
        active_back_leds[event.port - 1] = False

    def background_update(self, delta):
        if not self.enabled:
            return

        if self.lock.locked():  # e.g. if emotes are being displayed
            return

        for i in range(0, 6):
            if active_back_leds[i]:
                if settings.get("pattern_mirror_hexpansions", False):
                    tildagonos.leds[13 + i] = tildagonos.leds[1 + (i * 2)]
                else:
                    tildagonos.leds[13 + i] = led_colours[i]
            else:
                tildagonos.leds[13 + i] = (0, 0, 0)
        tildagonos.leds.write()
