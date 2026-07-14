import asyncio

import display
from events.input import Button, BUTTON_TYPES, ButtonDownEvent, ButtonUpEvent
from events.joystick import JOYSTICK_BUTTON_TYPES
import machine
from system.eventbus import eventbus
from tildagon import ePin
from . import FrontBoard
from system.hexpansion.events import HexpansionInsertionEvent, HexpansionRemovalEvent
import time
import frontboard2026
from frontboards.utils import detect_frontboard
from frontboards.cy8cmbrx import cy8cmbr3116_init
from frontboards.common import FRONTBOARD_BUTTON_TYPES

try:
    from _sim import _sim

    sim = True
except ImportError:
    sim = False


BUTTONS = {
    "A": Button(
        "A", "TwentyTwentySix", [BUTTON_TYPES["UP"], FRONTBOARD_BUTTON_TYPES["A"]]
    ),
    "B": Button(
        "B", "TwentyTwentySix", [BUTTON_TYPES["RIGHT"], FRONTBOARD_BUTTON_TYPES["B"]]
    ),
    "C": Button(
        "C", "TwentyTwentySix", [BUTTON_TYPES["CONFIRM"], FRONTBOARD_BUTTON_TYPES["C"]]
    ),
    "D": Button(
        "D", "TwentyTwentySix", [BUTTON_TYPES["DOWN"], FRONTBOARD_BUTTON_TYPES["D"]]
    ),
    "E": Button(
        "E", "TwentyTwentySix", [BUTTON_TYPES["LEFT"], FRONTBOARD_BUTTON_TYPES["E"]]
    ),
    "F": Button(
        "F", "TwentyTwentySix", [BUTTON_TYPES["CANCEL"], FRONTBOARD_BUTTON_TYPES["F"]]
    ),
}

JOYSTICK = {
    "UP": Button(
        "JOYUP", "TwentyTwentySix", [BUTTON_TYPES["UP"], JOYSTICK_BUTTON_TYPES["UP"]]
    ),
    "DOWN": Button(
        "JOYDOWN",
        "TwentyTwentySix",
        [BUTTON_TYPES["DOWN"], JOYSTICK_BUTTON_TYPES["DOWN"]],
    ),
    "LEFT": Button(
        "JOYLEFT",
        "TwentyTwentySix",
        [BUTTON_TYPES["LEFT"], JOYSTICK_BUTTON_TYPES["LEFT"]],
    ),
    "RIGHT": Button(
        "JOYRIGHT",
        "TwentyTwentySix",
        [BUTTON_TYPES["RIGHT"], JOYSTICK_BUTTON_TYPES["RIGHT"]],
    ),
    "FIRE": Button(
        "JOYFIRE",
        "TwentyTwentySix",
        [BUTTON_TYPES["CONFIRM"], JOYSTICK_BUTTON_TYPES["SELECT"]],
    ),
}


PROX = {
    "LEFTPROX": Button("LEFTPROX", "TwentyTwentySix"),
    "RIGHTPROX": Button("RIGHTPROX", "TwentyTwentySix"),
}

TOUCH = {
    "TOUCH01": Button("TOUCH01", "TwentyTwentySix"),
    "TOUCH02": Button("TOUCH02", "TwentyTwentySix"),
    "TOUCH03": Button("TOUCH03", "TwentyTwentySix"),
    "TOUCH04": Button("TOUCH04", "TwentyTwentySix"),
    "TOUCH05": Button("TOUCH05", "TwentyTwentySix"),
    "TOUCH06": Button("TOUCH06", "TwentyTwentySix"),
    "TOUCH07": Button("TOUCH07", "TwentyTwentySix"),
    "TOUCH08": Button("TOUCH08", "TwentyTwentySix"),
    "TOUCH09": Button("TOUCH09", "TwentyTwentySix"),
    "TOUCH10": Button("TOUCH10", "TwentyTwentySix"),
    "TOUCH11": Button("TOUCH11", "TwentyTwentySix"),
    "TOUCH12": Button("TOUCH12", "TwentyTwentySix"),
}


def joy_down(epin):
    for key in TwentyTwentySix.joy_assignment.keys():
        if TwentyTwentySix.joy_assignment[key] is epin:
            eventbus.emit(ButtonDownEvent(button=JOYSTICK[key]))
            TwentyTwentySix.joystick_states[key][0] = True
            print(f"{key} down")


def joy_up(epin):
    for key in TwentyTwentySix.joy_assignment.keys():
        if TwentyTwentySix.joy_assignment[key] is epin:
            eventbus.emit(ButtonUpEvent(button=JOYSTICK[key]))
            TwentyTwentySix.joystick_states[key][0] = False
            TwentyTwentySix.joystick_states[key][1] = 0
            print(f"{key} up")


def prox_down(prox):
    for key in TwentyTwentySix.PROX_INPUTS.keys():
        if TwentyTwentySix.PROX_INPUTS[key] is prox:
            eventbus.emit(ButtonDownEvent(button=PROX[key]))
            print(f"{key} down")


def prox_up(prox):
    for key in TwentyTwentySix.PROX_INPUTS.keys():
        if TwentyTwentySix.PROX_INPUTS[key] is prox:
            eventbus.emit(ButtonUpEvent(button=PROX[key]))
            print(f"{key} up")


def touch_down(touch):
    for key in TwentyTwentySix.TOUCH_INPUTS.keys():
        if TwentyTwentySix.TOUCH_INPUTS[key] is touch:
            eventbus.emit(ButtonDownEvent(button=TOUCH[key]))
            TwentyTwentySix.touch_states[key][0] = True
            print(f"{key} down")


def touch_up(touch):
    for key in TwentyTwentySix.TOUCH_INPUTS.keys():
        if TwentyTwentySix.TOUCH_INPUTS[key] is touch:
            eventbus.emit(ButtonUpEvent(button=TOUCH[key]))
            print(f"{key} up")
            TwentyTwentySix.touch_states[key][0] = False
            TwentyTwentySix.touch_states[key][1] = 0


class TwentyTwentySix(FrontBoard):
    JOY_PINS = {
        JOYSTICK["UP"]: (2, 6),
        JOYSTICK["DOWN"]: (1, 1),
        JOYSTICK["LEFT"]: (1, 3),
        JOYSTICK["RIGHT"]: (2, 7),
        JOYSTICK["FIRE"]: (1, 0),
    }
    BUTTON_PINS = {
        BUTTONS["A"]: (3, 10),
        BUTTONS["B"]: (3, 9),
        BUTTONS["C"]: (3, 8),
        BUTTONS["D"]: (3, 13),
        BUTTONS["E"]: (3, 12),
        BUTTONS["F"]: (3, 11),
    }
    PROX_INPUTS = {
        "LEFTPROX": frontboard2026.PROX1,
        "RIGHTPROX": frontboard2026.PROX2,
    }
    TOUCH_INPUTS = {
        "TOUCH01": frontboard2026.TOUCH01,
        "TOUCH02": frontboard2026.TOUCH02,
        "TOUCH03": frontboard2026.TOUCH03,
        "TOUCH04": frontboard2026.TOUCH04,
        "TOUCH05": frontboard2026.TOUCH05,
        "TOUCH06": frontboard2026.TOUCH06,
        "TOUCH07": frontboard2026.TOUCH07,
        "TOUCH08": frontboard2026.TOUCH08,
        "TOUCH09": frontboard2026.TOUCH09,
        "TOUCH10": frontboard2026.TOUCH10,
        "TOUCH11": frontboard2026.TOUCH11,
        "TOUCH12": frontboard2026.TOUCH12,
    }

    if detect_frontboard() == 0x2601:
        JOY_PINS[JOYSTICK["LEFT"]] = (1, 2)

    joy_assignment = {key: None for key in JOYSTICK.keys()}
    pin_assignment = {key: None for key in BUTTONS.keys()}
    button_states = {key: [False, 0] for key in BUTTONS.keys()}
    joystick_states = {key: [False, 0] for key in JOYSTICK.keys()}
    touch_states = {key: [False, 0] for key in TOUCH_INPUTS.keys()}
    hexpansion_states = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None}
    year = 2026
    num_pattern_leds = 12

    colors = {
        "pale_blue": (46, 173, 217),
        "mid_blue": (0, 93, 150),
        "dark_blue": (0, 7, 48),
        "green": (42, 226, 140),
        "yellow": (249, 226, 0),
        "orange": (247, 127, 2),
        "pink": (245, 81, 94),
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        # Duplicates of last year's special names, switched, for backwards compatibility
        "pale_green": (175, 201, 68),
        "mid_green": (82, 131, 41),
        "dark_green": (33, 48, 24),
        "blue": (42, 226, 140),
    }

    colors = {
        name: (c[0] / 256.0, c[1] / 256.0, c[2] / 256.0) for (name, c) in colors.items()
    }

    def header_gradient(self, ctx):
        return (
            ctx.linear_gradient(
                0.18 * 240 - 120, 0.5 * 240 - 120, 0.95 * 240 - 120, 0.5 * 240 - 120
            )
            .add_stop(0.0, self.colors["white"], 1.0)
            .add_stop(0.25, self.colors["yellow"], 1.0)
            .add_stop(0.5, self.colors["orange"], 1.0)
            .add_stop(0.75, self.colors["pink"], 1.0)
        )

    @property
    def ui_colors(self):
        return {
            "background": self.colors["dark_blue"],
            "label": self.colors["white"],
            "header": self.header_gradient,
            "menu_item": self.colors["white"],
            "active_menu_item": self.header_gradient,
            "button_background": self.colors["orange"],
            "button_radius": 5,
            "button_text": self.colors["black"],
            "active_button_background": self.colors["yellow"],
            "active_button_text": self.colors["black"],
            "notification": self.colors["pink"],
            "notification_text": self.colors["black"],
        }

    async def background_task(self):
        global sim
        reset = ePin((3, 7))
        display.gfx_init()
        cy8cmbr3116_init()
        reset.off()
        reset.on()

        for key in TwentyTwentySix.joy_assignment:
            gpio = self.JOY_PINS[JOYSTICK[key]]
            TwentyTwentySix.joy_assignment[key] = ePin(gpio)
            if not sim:
                TwentyTwentySix.joy_assignment[key].irq(
                    handler=joy_down, trigger=ePin.IRQ_FALLING
                )
                TwentyTwentySix.joy_assignment[key].irq(
                    handler=joy_up, trigger=ePin.IRQ_RISING
                )

        for key in TwentyTwentySix.pin_assignment:
            gpio = self.BUTTON_PINS[BUTTONS[key]]
            TwentyTwentySix.pin_assignment[key] = ePin(gpio)
        for key in TwentyTwentySix.PROX_INPUTS:
            if not sim:
                frontboard2026.set_cb(
                    TwentyTwentySix.PROX_INPUTS[key],
                    prox_down,
                    frontboard2026.IRQ_RISING,
                )
                frontboard2026.set_cb(
                    TwentyTwentySix.PROX_INPUTS[key],
                    prox_up,
                    frontboard2026.IRQ_FALLING,
                )
        for key in TwentyTwentySix.TOUCH_INPUTS:
            if not sim:
                frontboard2026.set_cb(
                    TwentyTwentySix.TOUCH_INPUTS[key],
                    touch_down,
                    frontboard2026.IRQ_RISING,
                )
                frontboard2026.set_cb(
                    TwentyTwentySix.TOUCH_INPUTS[key],
                    touch_up,
                    frontboard2026.IRQ_FALLING,
                )

        self.run_time = 0
        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, self.run_time) > 150:
                frontboard2026.run()
                self.run_time = now

            booped = not machine.Pin(0, mode=machine.Pin.IN).value()
            if booped:
                for i, gpio in enumerate(
                    map(lambda i: self.BUTTON_PINS[BUTTONS[i]], "ABCDEF")
                ):
                    state = TwentyTwentySix.hexpansion_states[i + 1]
                    button_down = not ePin(gpio).value()
                    if button_down and state is None:
                        TwentyTwentySix.hexpansion_states[i + 1] = now
                        await eventbus.emit_async(HexpansionInsertionEvent(port=i + 1))
                    elif state and time.ticks_diff(now, state) > 4000:
                        TwentyTwentySix.hexpansion_states[i + 1] = None
                        await eventbus.emit_async(HexpansionRemovalEvent(port=i + 1))
            else:
                if sim:
                    for i, key in enumerate(TwentyTwentySix.button_states.keys()):
                        button_down = not _sim.buttons.state()[i]
                        if button_down and not TwentyTwentySix.button_states[key][0]:
                            await eventbus.emit_async(
                                ButtonUpEvent(button=BUTTONS[key])
                            )
                        if not button_down and TwentyTwentySix.button_states[key][0]:
                            await eventbus.emit_async(
                                ButtonDownEvent(button=BUTTONS[key])
                            )
                        TwentyTwentySix.button_states[key][0] = button_down
                else:
                    for key in TwentyTwentySix.pin_assignment.keys():
                        button_down = not TwentyTwentySix.pin_assignment[key].value()
                        if button_down and not TwentyTwentySix.button_states[key][0]:
                            await eventbus.emit_async(
                                ButtonDownEvent(button=BUTTONS[key])
                            )
                            TwentyTwentySix.button_states[key][1] = now
                        elif button_down:
                            if (
                                time.ticks_diff(
                                    now, TwentyTwentySix.button_states[key][1]
                                )
                                > 200
                            ):
                                await eventbus.emit_async(
                                    ButtonDownEvent(button=BUTTONS[key])
                                )
                                TwentyTwentySix.button_states[key][1] = now
                        if not button_down and TwentyTwentySix.button_states[key][0]:
                            await eventbus.emit_async(
                                ButtonUpEvent(button=BUTTONS[key])
                            )
                        TwentyTwentySix.button_states[key][0] = button_down

                    for key in TwentyTwentySix.joystick_states.keys():
                        if (
                            TwentyTwentySix.joystick_states[key][0]
                            and not TwentyTwentySix.joystick_states[key][1]
                        ):
                            TwentyTwentySix.joystick_states[key][1] = now
                        elif TwentyTwentySix.joystick_states[key][0]:
                            if (
                                time.ticks_diff(
                                    now, TwentyTwentySix.joystick_states[key][1]
                                )
                                > 200
                            ):
                                await eventbus.emit_async(
                                    ButtonDownEvent(button=JOYSTICK[key])
                                )
                                TwentyTwentySix.joystick_states[key][1] = now

            await asyncio.sleep(0.01)
