from app import App
from tildagonos import tildagonos
import settings
import asyncio
import os
from system.patterndisplay.events import (
    PatternEnable,
    PatternDisable,
    PatternReload,
    PatternSet,
)
from system.eventbus import eventbus
from app_components.utils import path_isfile
from firmware_apps.settings_app import PAT_DIR


class PatternDisplay(App):
    def __init__(self):
        self._p = None
        eventbus.on_async(PatternEnable, self._enable, self)
        eventbus.on_async(PatternDisable, self._disable, self)
        eventbus.on_async(PatternReload, self._reload, self)
        eventbus.on_async(PatternSet, self._set, self)
        self.load_pattern()
        self.enabled = settings.get("pattern_generator_enabled", True)

    def load_pattern(self):
        self.pattern = settings.get("pattern", ("rainbow", None))
        print(self.pattern)
        if len(self.pattern) != 2:
            self.pattern = (self.pattern, None)
        print("Loading pattern: %s" % self.pattern[0])
        if self.pattern[1]:
            path = f"/pattern/{self.pattern[1]}/app.py"
            print(path)
            try:
                os.mkdir(PAT_DIR)
            except OSError:
                pass
            if path_isfile(path):
                try:
                    _patternpath = f"pattern.{self.pattern[1]}.app"
                    _patternclass = "__Pattern_export__"
                    _pmodule = __import__(
                        _patternpath,
                        globals(),
                        locals(),
                        [
                            _patternclass,
                        ],
                    )
                    _pclass = getattr(_pmodule, _patternclass)
                    self._p = _pclass()
                except ImportError:
                    raise ImportError(f"Pattern {path} not found!")
            else:
                settings.set("pattern", ("rainbow", None))
        if self.pattern[1] is None:
            try:
                _patternpath = "patterns." + self.pattern[0]
                _patternclass = (
                    self.pattern[0][0].upper() + self.pattern[0][1:] + "Pattern"
                )
                _pmodule = __import__(
                    _patternpath,
                    globals(),
                    locals(),
                    [
                        _patternclass,
                    ],
                )
                _pclass = getattr(_pmodule, _patternclass)
                self._p = _pclass()
            except ImportError:
                raise ImportError(f"Pattern {self.pattern} not found!")

    async def _enable(self, event: PatternEnable):
        self.enabled = True

    async def _disable(self, event: PatternDisable):
        self.enabled = False

    async def _reload(self, event: PatternReload):
        self.load_pattern()

    async def _set(self, event: PatternSet):
        self._p = event.pattern_class()

    async def background_task(self):
        while True:
            if self._p:
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
            else:
                await asyncio.sleep(1)


__app_export__ = PatternDisplay
