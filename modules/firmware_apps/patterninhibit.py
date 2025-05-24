import asyncio
import app

from events.input import Buttons, BUTTON_TYPES
from system.eventbus import eventbus
from system.patterndisplay.events import PatternEnable, PatternDisable

from tildagonos import tildagonos


class PatternInhibit(app.App):
    def __init__(self):
        super().__init__()
        self.button_states = Buttons(self)
        eventbus.emit(PatternDisable())
        self._make_red()
        self._inhibiting = True

    def _make_red(self):
        asyncio.sleep(0.5)
        for i in range(1, 13):
            tildagonos.leds[i] = (int(i * (255 / 12)), 0, 0)
        tildagonos.leds.write()

    def update(self, delta):
        if self.button_states.get(BUTTON_TYPES["CANCEL"]):
            eventbus.emit(PatternDisable())
            self._inhibiting = True
            self._make_red()
        elif self.button_states.get(BUTTON_TYPES["CONFIRM"]):
            eventbus.emit(PatternEnable())
            self._inhibiting = False

    def draw(self, ctx):
        ctx.save()
        ctx.font_size = 20
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        if self._inhibiting:
            ctx.rgb(0.2, 0, 0).rectangle(-120, -120, 240, 240).fill()
            ctx.rgb(1, 0, 0).move_to(0, 0).text("Inhibiting LEDs")
        else:
            ctx.rgb(0, 0.2, 0).rectangle(-120, -120, 240, 240).fill()
            ctx.rgb(0, 1, 0).move_to(0, 0).text("Not Inhibiting LEDs")
        ctx.restore()
