from app import App
from tildagonos import tildagonos
import settings
import asyncio


class PatternDisplay(App):
    def __init__(self):
        self.pattern = settings.get("pattern", "rainbow")
        try:
            _patternpath = "patterns." + self.pattern
            _patternclass = self.pattern[0].upper() + self.pattern[1:] + "Pattern"
            _pmodule = __import__(_patternpath, globals(), locals(), [_patternclass])
            _pclass = getattr(_pmodule, _patternclass)
            self._p = _pclass()
        except:
            raise ImportError(f"Pattern {self.pattern} not found!")

    async def background_task(self):
        while True:
            next_frame = self._p.next()
            for l in range(12):
                tildagonos.leds[l + 1] = next_frame[l]
            tildagonos.leds.write()
            await asyncio.sleep(1 / self._p.fps)


__app_export__ = PatternDisplay
