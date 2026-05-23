from random import random

from events.input import Buttons
from system.eventbus import eventbus
from system.patterndisplay.events import PatternDisable, PatternEnable

import app

from .base.conf import conf
from .base.terminate import terminate
from .common.colour_tools import rgb_from_hue
from .common.led_lighter import LEDLighter
from .boopscreen.logo import Logo

from app_components.tokens import clear_background


class BoopSpinner(app.App):
    """Spinning Boop Screen."""

    def __init__(self):
        """Construct."""
        eventbus.emit(PatternDisable())
        self.button_states = Buttons(self)
        self.hue = random()
        self.rotation = conf["rotation"]["start"]
        self.fading = False
        self.logo = Logo()
        self.logo.scale = 0
        self.logo.opacity = 1

        self.leds = LEDLighter(brightness=conf["leds"]["start"])

    def update(self, _):
        """Update."""
        colour = rgb_from_hue(self.hue)

        self.logo.grow()
        self.logo.colour = colour

        self.rotation += conf["rotation"]["rate"]
        self.hue += conf["hue-increment"]

        if self.logo.full_grown():
            self.fading = True

        if self.fading:
            self.logo.fade()

        elif self.leds.brightness < conf["leds"]["max"]:
            self.leds.brightness += conf["leds"]["increment"]

        self.leds.from_rgb([int(x * 255) for x in colour])

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
