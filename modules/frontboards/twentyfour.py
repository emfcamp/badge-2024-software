import asyncio

import display
from events.input import Button, BUTTON_TYPES, ButtonDownEvent, ButtonUpEvent
import machine
from system.eventbus import eventbus
from tildagonos import tildagonos
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
        BUTTONS["A"]: (0x5A, 0, (1 << 6)),
        BUTTONS["B"]: (0x5A, 0, (1 << 7)),
        BUTTONS["C"]: (0x59, 0, (1 << 0)),
        BUTTONS["D"]: (0x59, 0, (1 << 1)),
        BUTTONS["E"]: (0x59, 0, (1 << 2)),
        BUTTONS["F"]: (0x59, 0, (1 << 3)),
    }

    async def background_task(self):
        display.gfx_init()

        button_states = {button: False for button in self.BUTTON_PINS.keys()}
        hexpansion_states = {
            1: {"inserted": None, "removed": None},
            2: {"inserted": None, "removed": None},
            3: {"inserted": None, "removed": None},
            4: {"inserted": None, "removed": None},
            5: {"inserted": None, "removed": None},
            6: {"inserted": None, "removed": None},
        }
        while True:
            booped = not machine.Pin(0, mode=machine.Pin.IN).value()
            tildagonos.read_egpios()
            if booped:
                now = time.ticks_ms()
                for i, gpio in enumerate(
                    map(lambda i: self.BUTTON_PINS[BUTTONS[i]], "ABCDEF")
                ):
                    inserted_state = hexpansion_states[i + 1]['inserted']
                    removed_state = hexpansion_states[i + 1]['removed']
                    button_down = not tildagonos.check_egpio_state(
                        gpio, readgpios=False
                    )
                    # print(i, now, state)
                    if (
                        button_down
                        and inserted_state is None
                        and time.ticks_diff(now, removed_state) > 1000
                    ):
                        hexpansion_states[i + 1]['inserted'] = now
                        hexpansion_states[i + 1]['removed'] = None
                        await eventbus.emit_async(HexpansionInsertionEvent(port=i + 1))
                    elif (
                        button_down
                        and inserted_state
                        and time.ticks_diff(now, inserted_state) > 1000
                    ):
                        hexpansion_states[i + 1]['inserted'] = None
                        hexpansion_states[i + 1]['removed'] = now
                        # print(f"Removing {i}")
                        await eventbus.emit_async(HexpansionRemovalEvent(port=i + 1))
            else:
                for button, pin in self.BUTTON_PINS.items():
                    button_down = not tildagonos.check_egpio_state(pin, readgpios=False)
                    if button_down and not button_states[button]:
                        await eventbus.emit_async(ButtonDownEvent(button=button))
                    if not button_down and button_states[button]:
                        await eventbus.emit_async(ButtonUpEvent(button=button))
                    button_states[button] = button_down
            await asyncio.sleep(0.01)
