from random import choice

from events.input import Buttons
from system.eventbus import eventbus
from system.patterndisplay.events import PatternDisable, PatternEnable

import app

from .boopscreen.conf import conf
from .boopscreen.terminate import terminate
from .boopscreen.led_lighter import LEDLighter
from .boopscreen.logo import Logo

from app_components.tokens import clear_background


class BoopSpinner(app.App):
    """Spinning Boop Screen."""

    def __init__(self):
        """Construct."""
        eventbus.emit(PatternDisable())
        self.button_states = Buttons(self)
        self.rotation = conf["rotation"]["start"]
        self.fading = False

        self.colours = choice(conf["colours"])

        self.logo = Logo(colour=self.colours["decimal"])
        self.logo.scale = 0
        self.logo.opacity = 1

        self.leds = LEDLighter(
            colour=self.colours["rgb"], brightness=conf["leds"]["start"]
        )

    def update(self, _):
        """Update."""
        self.logo.grow()

        self.rotation += conf["rotation"]["rate"]

        if self.logo.full_grown():
            self.fading = True

        if self.fading:
            self.logo.fade()

        elif self.leds.brightness < conf["leds"]["max"]:
            self.leds.brightness += conf["leds"]["increment"]

        self.leds.light()

        if self.logo.faded():
            eventbus.emit(PatternEnable())
            terminate(self)

    def draw(self, ctx):
        """Draw."""
        ctx.rotate(self.rotation)
        clear_background(ctx)
        self.overlays = [self.logo]
        self.draw_overlays(ctx)


__app_export__ = BoopSpinner
