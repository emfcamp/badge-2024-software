from app import App
from tildagonos import tildagonos
import settings
import asyncio
import os
import sys
import neopixel
from system.patterndisplay.events import (
    PatternEnable,
    PatternDisable,
    PatternReload,
    PatternSet,
)
from system.eventbus import eventbus
from app_components.utils import path_isfile
from firmware_apps.settings_app import PAT_DIR
from system.notification.events import ShowNotificationEvent
from frontboards.twentysix import TwentyTwentySix


class PatternDisplay(App):
    def __init__(self):
        self._p = None
        eventbus.on_async(PatternEnable, self._enable, self)
        eventbus.on_async(PatternDisable, self._disable, self)
        eventbus.on_async(PatternReload, self._reload, self)
        eventbus.on_async(PatternSet, self._set, self)
        self.load_pattern()
        self.enabled = settings.get("pattern_generator_enabled", True)
        self.correction = neopixel.DimCorrection(1.0)
        self.leds = neopixel.CorrectedNeoPixel(
            neopixel.ComposedNeoPixel(tildagonos.leds, -1),
            [self.correction] * 12 + [None] * 6,
        )
        self.TOUCH_KEYS = [
            "TOUCH01",
            "TOUCH02",
            "TOUCH03",
            "TOUCH04",
            "TOUCH05",
            "TOUCH06",
            "TOUCH07",
            "TOUCH08",
            "TOUCH09",
            "TOUCH10",
            "TOUCH11",
            "TOUCH12",
        ]

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
                    _patternclass = "__pattern_export__"
                    _pmodule = __import__(
                        _patternpath,
                        globals(),
                        locals(),
                        [
                            _patternclass,
                        ],
                    )
                    _pclass = getattr(_pmodule, _patternclass)
                    try:
                        self._p = _pclass(12)
                    except TypeError:
                        self._p = _pclass()
                except ImportError:
                    raise ImportError(f"Pattern {path} not found!")
                except Exception as e:
                    sys.print_exception(e)
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
                try:
                    self._p = _pclass(12)
                except TypeError:
                    self._p = _pclass()
            except ImportError:
                raise ImportError(f"Pattern {self.pattern} not found!")
            except Exception as e:
                sys.print_exception(e)

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
                try:
                    self.correction.amount = settings.get("pattern_brightness", 0.1)
                    next_frame = self._p.next()
                    if self.enabled:
                        for led in range(12):
                            if TwentyTwentySix.touch_states[self.TOUCH_KEYS[led]][0]:
                                self.leds[led] = (255, 255, 255)
                            else:
                                self.leds[led] = next_frame[led]
                        self.leds.write()
                    if not self._p.fps:
                        break
                    await asyncio.sleep(1 / self._p.fps)
                except Exception as e:
                    print(f"Error creating pattern: {e}")
                    eventbus.emit(
                        ShowNotificationEvent(
                            message=f"Pattern {self.pattern[0]} has crashed"
                        )
                    )
                    self._p = None
                    await asyncio.sleep(1)
            else:
                await asyncio.sleep(1)


__app_export__ = PatternDisplay
