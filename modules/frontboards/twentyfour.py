import asyncio

import display
from events.input import Button, BUTTON_TYPES, ButtonDownEvent, ButtonUpEvent
import machine
from system.eventbus import eventbus
from tildagon import ePin
from . import FrontBoard
from system.hexpansion.events import HexpansionInsertionEvent, HexpansionRemovalEvent
import time
from frontboards.common import FRONTBOARD_BUTTON_TYPES

try:
    from _sim import _sim

    sim = True
except ImportError:
    sim = False


BUTTONS = {
    "A": Button(
        "A", "TwentyTwentyFour", [BUTTON_TYPES["UP"], FRONTBOARD_BUTTON_TYPES["A"]]
    ),
    "B": Button(
        "B", "TwentyTwentyFour", [BUTTON_TYPES["RIGHT"], FRONTBOARD_BUTTON_TYPES["B"]]
    ),
    "C": Button(
        "C", "TwentyTwentyFour", [BUTTON_TYPES["CONFIRM"], FRONTBOARD_BUTTON_TYPES["C"]]
    ),
    "D": Button(
        "D", "TwentyTwentyFour", [BUTTON_TYPES["DOWN"], FRONTBOARD_BUTTON_TYPES["D"]]
    ),
    "E": Button(
        "E", "TwentyTwentyFour", [BUTTON_TYPES["LEFT"], FRONTBOARD_BUTTON_TYPES["E"]]
    ),
    "F": Button(
        "F", "TwentyTwentyFour", [BUTTON_TYPES["CANCEL"], FRONTBOARD_BUTTON_TYPES["F"]]
    ),
}


def buttondown(epin):
    booped = not machine.Pin(0, mode=machine.Pin.IN).value()
    hexindex = 1
    for key in TwentyTwentyFour.pin_assignment.keys():
        if TwentyTwentyFour.pin_assignment[key] is epin:
            if booped:
                now = time.ticks_ms()
                if TwentyTwentyFour.hexpansion_states[hexindex] is None:
                    TwentyTwentyFour.hexpansion_states[hexindex] = now
                    eventbus.emit(HexpansionInsertionEvent(port=hexindex))
                hexindex += 1
            else:
                eventbus.emit(ButtonDownEvent(button=BUTTONS[key]))
                TwentyTwentyFour.button_states[key][0] = True


def buttonup(epin):
    for key in TwentyTwentyFour.pin_assignment.keys():
        if TwentyTwentyFour.pin_assignment[key] is epin:
            eventbus.emit(ButtonUpEvent(button=BUTTONS[key]))
            TwentyTwentyFour.button_states[key][0] = False
            TwentyTwentyFour.button_states[key][1] = 0


def scale_color(c):
    return (c[0] / 256.0, c[1] / 256.0, c[2] / 256.0)


class TwentyTwentyFour(FrontBoard):
    BUTTON_PINS = {
        BUTTONS["A"]: (2, 6),
        BUTTONS["B"]: (2, 7),
        BUTTONS["C"]: (1, 0),
        BUTTONS["D"]: (1, 1),
        BUTTONS["E"]: (1, 2),
        BUTTONS["F"]: (1, 3),
    }
    pin_assignment = {key: None for key in BUTTONS.keys()}
    button_states = {key: [False, 0] for key in BUTTONS.keys()}
    hexpansion_states = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None}
    year = 2024
    num_pattern_leds = 12

    colors = {
        "pale_green": (175, 201, 68),
        "mid_green": (82, 131, 41),
        "dark_green": (33, 48, 24),
        "yellow": (249, 226, 0),
        "orange": (246, 127, 2),
        "pink": (245, 80, 137),
        "blue": (46, 173, 217),
        "black": (0, 0, 0),
        "white": (255, 255, 255),
    }

    colors = {
        name: (c[0] / 256.0, c[1] / 256.0, c[2] / 256.0) for (name, c) in colors.items()
    }

    ui_colors = {
        "background": colors["dark_green"],
        "label": colors["white"],
        "header": colors["white"],
        "menu_item": colors["white"],
        "active_menu_item": colors["white"],
        "button_background": colors["pale_green"],
        "button_radius": 30,
        "button_text": colors["black"],
        "active_button_background": colors["yellow"],
        "active_button_text": colors["black"],
    }

    async def background_task(self):
        global sim
        display.gfx_init()
        for key in TwentyTwentyFour.pin_assignment:
            gpio = self.BUTTON_PINS[BUTTONS[key]]
            TwentyTwentyFour.pin_assignment[key] = ePin(gpio)
            if not sim:
                TwentyTwentyFour.pin_assignment[key].irq(
                    handler=buttondown, trigger=ePin.IRQ_FALLING
                )
                TwentyTwentyFour.pin_assignment[key].irq(
                    handler=buttonup, trigger=ePin.IRQ_RISING
                )

        while True:
            booped = not machine.Pin(0, mode=machine.Pin.IN).value()
            if booped:
                now = time.ticks_ms()
                for i, gpio in enumerate(
                    map(lambda i: self.BUTTON_PINS[BUTTONS[i]], "ABCDEF")
                ):
                    state = TwentyTwentyFour.hexpansion_states[i + 1]
                    if state and time.ticks_diff(now, state) > 4000:
                        TwentyTwentyFour.hexpansion_states[i + 1] = None
                        await eventbus.emit_async(HexpansionRemovalEvent(port=i + 1))
            else:
                if sim:
                    for i, key in enumerate(TwentyTwentyFour.button_states.keys()):
                        button_down = not _sim.buttons.state()[i]
                        if button_down and not TwentyTwentyFour.button_states[key][0]:
                            await eventbus.emit_async(
                                ButtonUpEvent(button=BUTTONS[key])
                            )
                        if not button_down and TwentyTwentyFour.button_states[key][0]:
                            await eventbus.emit_async(
                                ButtonDownEvent(button=BUTTONS[key])
                            )
                        TwentyTwentyFour.button_states[key][0] = button_down
                else:
                    for key in TwentyTwentyFour.button_states.keys():
                        if TwentyTwentyFour.button_states[key][0]:
                            if TwentyTwentyFour.button_states[key][1] > 4:
                                await eventbus.emit_async(
                                    ButtonDownEvent(button=BUTTONS[key])
                                )
                            else:
                                TwentyTwentyFour.button_states[key][1] += 1
            await asyncio.sleep(0.1)
