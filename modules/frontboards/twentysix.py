import asyncio

import display
from events.input import Button, BUTTON_TYPES, ButtonDownEvent, ButtonUpEvent
import machine
from system.eventbus import eventbus
from tildagon import ePin
from . import FrontBoard
from system.hexpansion.events import HexpansionInsertionEvent, HexpansionRemovalEvent
import time
import frontboard2026

try:
    from _sim import _sim

    sim = True
except ImportError:
    sim = False


BUTTONS = {
    "A": Button("A", "TwentyTwentySix", BUTTON_TYPES["A"]),
    "B": Button("B", "TwentyTwentySix", BUTTON_TYPES["B"]),
    "C": Button("C", "TwentyTwentySix", BUTTON_TYPES["C"]),
    "D": Button("D", "TwentyTwentySix", BUTTON_TYPES["D"]),
    "E": Button("E", "TwentyTwentySix", BUTTON_TYPES["E"]),
    "CANCEL": Button("CANCEL", "TwentyTwentySix", BUTTON_TYPES["CANCEL"]),
}

JOYSTICK = {
    "UP": Button("UP", "TwentyTwentySix", BUTTON_TYPES["UP"]),
    "DOWN": Button("DOWN", "TwentyTwentySix", BUTTON_TYPES["DOWN"]),
    "LEFT": Button("LEFT", "TwentyTwentySix", BUTTON_TYPES["LEFT"]),
    "RIGHT": Button("RIGHT", "TwentyTwentySix", BUTTON_TYPES["RIGHT"]),
    "CONFIRM": Button("CONFIRM", "TwentyTwentySix", BUTTON_TYPES["CONFIRM"]),
}


PROX = {
    "LEFTPROX": Button("LEFTPROX", "TwentyTwentySix", BUTTON_TYPES["LEFTPROX"]),
    "RIGHTPROX": Button("RIGHTPROX", "TwentyTwentySix", BUTTON_TYPES["RIGHTPROX"]),
}

TOUCH = {
    "TOUCH1": Button("TOUCH1", "TwentyTwentySix", BUTTON_TYPES["TOUCH1"]),
    "TOUCH2": Button("TOUCH2", "TwentyTwentySix", BUTTON_TYPES["TOUCH2"]),
    "TOUCH3": Button("TOUCH3", "TwentyTwentySix", BUTTON_TYPES["TOUCH3"]),
    "TOUCH4": Button("TOUCH4", "TwentyTwentySix", BUTTON_TYPES["TOUCH4"]),
    "TOUCH5": Button("TOUCH5", "TwentyTwentySix", BUTTON_TYPES["TOUCH5"]),
    "TOUCH6": Button("TOUCH6", "TwentyTwentySix", BUTTON_TYPES["TOUCH6"]),
    "TOUCH7": Button("TOUCH7", "TwentyTwentySix", BUTTON_TYPES["TOUCH7"]),
    "TOUCH8": Button("TOUCH8", "TwentyTwentySix", BUTTON_TYPES["TOUCH8"]),
    "TOUCH9": Button("TOUCH9", "TwentyTwentySix", BUTTON_TYPES["TOUCH9"]),
    "TOUCH10": Button("TOUCH10", "TwentyTwentySix", BUTTON_TYPES["TOUCH10"]),
    "TOUCH11": Button("TOUCH11", "TwentyTwentySix", BUTTON_TYPES["TOUCH11"]),
    "TOUCH12": Button("TOUCH12", "TwentyTwentySix", BUTTON_TYPES["TOUCH12"]),
}


def buttondown(epin):
    booped = not machine.Pin(0, mode=machine.Pin.IN).value()
    hexindex = 1
    for key in TwentyTwentySix.pin_assignment.keys():
        if TwentyTwentySix.pin_assignment[key] is epin:
            if booped:
                now = time.ticks_ms()
                if TwentyTwentySix.hexpansion_states[hexindex] is None:
                    TwentyTwentySix.hexpansion_states[hexindex] = now
                    eventbus.emit_async(HexpansionInsertionEvent(port=hexindex))
                hexindex += 1
            else:
                eventbus.emit(ButtonDownEvent(button=BUTTONS[key]))
                TwentyTwentySix.button_states[key][0] = True


def buttonup(epin):
    for key in TwentyTwentySix.pin_assignment.keys():
        if TwentyTwentySix.pin_assignment[key] is epin:
            eventbus.emit(ButtonUpEvent(button=BUTTONS[key]))
            TwentyTwentySix.button_states[key][0] = False
            TwentyTwentySix.button_states[key][1] = 0


def joy_down(epin):
    for key in TwentyTwentySix.joy_assignment.keys():
        if TwentyTwentySix.joy_assignment[key] is epin:
            eventbus.emit(ButtonDownEvent(button=JOYSTICK[key]))
            TwentyTwentySix.joystick_states[key][0] = True


def joy_up(epin):
    for key in TwentyTwentySix.joy_assignment.keys():
        if TwentyTwentySix.joy_assignment[key] is epin:
            eventbus.emit(ButtonUpEvent(button=JOYSTICK[key]))
            TwentyTwentySix.joystick_states[key][0] = False
            TwentyTwentySix.joystick_states[key][1] = 0


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
        JOYSTICK["LEFT"]: (1, 2),
        JOYSTICK["RIGHT"]: (2, 7),
        JOYSTICK["CONFIRM"]: (1, 0),
    }
    BUTTON_PINS = {
        BUTTONS["A"]: (3, 10),
        BUTTONS["B"]: (3, 9),
        BUTTONS["C"]: (3, 8),
        BUTTONS["D"]: (3, 13),
        BUTTONS["E"]: (3, 12),
        BUTTONS["CANCEL"]: (3, 11),
    }
    PROX_INPUTS = {
        "LEFTPROX": frontboard2026.PROX1,
        "RIGHTPROX": frontboard2026.PROX2,
    }
    TOUCH_INPUTS = {
        "TOUCH1": frontboard2026.TOUCH1,
        "TOUCH2": frontboard2026.TOUCH2,
        "TOUCH3": frontboard2026.TOUCH3,
        "TOUCH4": frontboard2026.TOUCH4,
        "TOUCH5": frontboard2026.TOUCH5,
        "TOUCH6": frontboard2026.TOUCH6,
        "TOUCH7": frontboard2026.TOUCH7,
        "TOUCH8": frontboard2026.TOUCH8,
        "TOUCH9": frontboard2026.TOUCH9,
        "TOUCH10": frontboard2026.TOUCH10,
        "TOUCH11": frontboard2026.TOUCH11,
        "TOUCH12": frontboard2026.TOUCH12,
    }

    joy_assignment = {key: None for key in JOYSTICK.keys()}
    pin_assignment = {key: None for key in BUTTONS.keys()}
    button_states = {key: [False, 0] for key in BUTTONS.keys()}
    joystick_states = {key: [False, 0] for key in JOYSTICK.keys()}
    touch_states = {key: [False, 0] for key in TOUCH_INPUTS.keys()}
    hexpansion_states = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None}
    year = 2026
    num_pattern_leds = 12

    async def background_task(self):
        global sim
        reset = ePin((3, 7))
        display.gfx_init()
        # cy8cmbr3116_init()
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
            if not sim:
                TwentyTwentySix.pin_assignment[key].irq(
                    handler=buttondown, trigger=ePin.IRQ_FALLING
                )
                TwentyTwentySix.pin_assignment[key].irq(
                    handler=buttonup, trigger=ePin.IRQ_RISING
                )
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

        while True:
            frontboard2026.run()
            booped = not machine.Pin(0, mode=machine.Pin.IN).value()
            if booped:
                now = time.ticks_ms()
                for i, gpio in enumerate(
                    map(lambda i: self.BUTTON_PINS[BUTTONS[i]], "ABCDEF")
                ):
                    state = TwentyTwentySix.hexpansion_states[i + 1]
                    if state and time.ticks_diff(now, state) > 4000:
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
                    for key in TwentyTwentySix.button_states.keys():
                        if TwentyTwentySix.button_states[key][0]:
                            if TwentyTwentySix.button_states[key][1] > 4:
                                await eventbus.emit_async(
                                    ButtonDownEvent(button=BUTTONS[key])
                                )
                            else:
                                TwentyTwentySix.button_states[key][1] += 1
                    for key in TwentyTwentySix.joystick_states.keys():
                        if TwentyTwentySix.joystick_states[key][0]:
                            if TwentyTwentySix.joystick_states[key][1] > 4:
                                await eventbus.emit_async(
                                    ButtonDownEvent(button=JOYSTICK[key])
                                )
                            else:
                                TwentyTwentySix.joystick_states[key][1] += 1

            await asyncio.sleep(0.15)
