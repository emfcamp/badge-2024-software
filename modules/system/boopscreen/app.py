from math import degrees, pi, sin
from random import random

from events.input import BUTTON_TYPES, Buttons
from system.eventbus import eventbus
from system.patterndisplay.events import PatternDisable, PatternEnable

import app

from .base.background import Background
from .base.conf import conf
from .base.terminate import terminate
from .common.colour_tools import rgb_from_hue
from .common.led_lighter import LEDLighter
from .boopscreen.logo import Logo



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

        self.leds = LEDLighter(brightness=0)

    def update(self, _):
        """Update."""
        self.scan_buttons()
        colour = rgb_from_hue(self.hue)

        self.logo.grow()
        self.logo.colour = colour

        self.rotation += conf["rotation"]["rate"]
        self.hue += conf["hue-increment"]

        if self.logo.full_grown():
            self.fading = True

        if self.fading:
            self.logo.fade()
            if self.leds.brightness > 0:
                self.leds.brightness -= conf["leds"]["increment"]

        elif self.leds.brightness < conf["leds"]["max"]:
            self.leds.brightness += conf["leds"]["increment"]

        self.leds.from_rgb([int(x * 255) for x in colour])

        if self.logo.faded():
            eventbus.emit(PatternEnable())
            terminate(self)

    def draw(self, ctx):
        """Draw."""
        ctx.rotate(self.rotation)
        self.overlays = []
        self.overlays.append(
            Background(colour=(0, 0, 0), opacity=conf["background-opacity"])
        )

        self.overlays.append(self.logo)

        self.draw_overlays(ctx)

    def scan_buttons(self):
        """Buttons."""
        if self.button_states.get(BUTTON_TYPES["CANCEL"]):
            self.button_states.clear()
            terminate(self)


__app_export__ = BoopSpinner
