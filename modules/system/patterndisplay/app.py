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
            brightness = settings.get("pattern_brightness", 1.0)
            next_frame = self._p.next()
            for l in range(12):
                if brightness < 1.0:
                    tildagonos.leds[l + 1] = tuple(int(i*brightness) for i in next_frame[l])
                else:
                    tildagonos.leds[l + 1] = next_frame[l]
            tildagonos.leds.write()
            if not self._p.fps:
                break
            await asyncio.sleep(1 / self._p.fps)


__app_export__ = PatternDisplay
