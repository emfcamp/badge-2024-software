import asyncio

import display
from events.input import Button, BUTTON_TYPES, ButtonDownEvent, ButtonUpEvent
import machine
from system.eventbus import eventbus
from tildagon import ePin
from . import FrontBoard
from system.hexpansion.events import HexpansionInsertionEvent, HexpansionRemovalEvent
import time


BUTTONS = {
    "A": Button("A", "TwentyTwentyFour", BUTTON_TYPES["UP"]),
    "B": Button("B", "TwentyTwentyFour", BUTTON_TYPES["RIGHT"]),
    "C": Button("C", "TwentyTwentyFour", BUTTON_TYPES["CONFIRM"]),
    "D": Button("D", "TwentyTwentyFour", BUTTON_TYPES["DOWN"]),
    "E": Button("E", "TwentyTwentyFour", BUTTON_TYPES["LEFT"]),
    "F": Button("F", "TwentyTwentyFour", BUTTON_TYPES["CANCEL"]),
}


class TwentyTwentyFour(FrontBoard):
    BUTTON_PINS = {
        BUTTONS["A"]: (2, 6),
        BUTTONS["B"]: (2, 7),
        BUTTONS["C"]: (1, 0),
        BUTTONS["D"]: (1, 1),
        BUTTONS["E"]: (1, 2),
        BUTTONS["F"]: (1, 3),
    }

    async def background_task(self):
        display.gfx_init()

        button_states = {button: False for button in self.BUTTON_PINS.keys()}
        hexpansion_states = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None}
        while True:
            booped = not machine.Pin(0, mode=machine.Pin.IN).value()
            if booped:
                now = time.ticks_ms()
                for i, gpio in enumerate(
                    map(lambda i: self.BUTTON_PINS[BUTTONS[i]], "ABCDEF")
                ):
                    state = hexpansion_states[i + 1]
                    button_down = not ePin(gpio).value()
                    # print(i, now, state)
                    if button_down and state is None:
                        hexpansion_states[i + 1] = now
                        await eventbus.emit_async(HexpansionInsertionEvent(port=i + 1))
                    elif state and time.ticks_diff(now, state) > 4000:
                        hexpansion_states[i + 1] = None
                        # print(f"Removing {i}")
                        await eventbus.emit_async(HexpansionRemovalEvent(port=i + 1))
            else:
                for button, pin in self.BUTTON_PINS.items():
                    button_down = not ePin(pin).value()
                    if button_down and not button_states[button]:
                        await eventbus.emit_async(ButtonDownEvent(button=button))
                    if not button_down and button_states[button]:
                        await eventbus.emit_async(ButtonUpEvent(button=button))
                    button_states[button] = button_down
            await asyncio.sleep(0.01)
