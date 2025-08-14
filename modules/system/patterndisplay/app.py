from app import App
from tildagonos import tildagonos
import settings
import asyncio
from system.patterndisplay.events import PatternEnable, PatternDisable, PatternReload
from system.eventbus import eventbus


class PatternDisplay(App):
    def __init__(self):
        super().__init__()
        eventbus.on_async(PatternEnable, self._enable, self)
        eventbus.on_async(PatternDisable, self._disable, self)
        eventbus.on_async(PatternReload, self._reload, self)
        self.load_pattern()
        self.enabled = settings.get("pattern_generator_enabled", True)

    def load_pattern(self):
        self.pattern = settings.get("pattern", "rainbow")
        print("Loading pattern: %s" % self.pattern)
        try:
            _patternpath = "patterns." + self.pattern
            _patternclass = self.pattern[0].upper() + self.pattern[1:] + "Pattern"
            _pmodule = __import__(_patternpath, globals(), locals(), [_patternclass])
            _pclass = getattr(_pmodule, _patternclass)
            self._p = _pclass()
        except ModuleNotFoundError:
            raise ImportError(f"Pattern {self.pattern} not found!")

    async def _enable(self, event: PatternEnable):
        self.enabled = True

    async def _disable(self, event: PatternDisable):
        self.enabled = False

    async def _reload(self, event: PatternReload):
        self.load_pattern()

    async def background_task(self):
        while True:
            brightness = settings.get("pattern_brightness", 0.1)
            next_frame = self._p.next()
            if self.enabled:
                for led in range(12):
                    if brightness < 1.0:
                        tildagonos.leds[led + 1] = tuple(
                            int(i * brightness) for i in next_frame[led]
                        )
                    else:
                        tildagonos.leds[led + 1] = next_frame[led]
                tildagonos.leds.write()
            if not self._p.fps:
                break
            await asyncio.sleep(1 / self._p.fps)


__app_export__ = PatternDisplay
