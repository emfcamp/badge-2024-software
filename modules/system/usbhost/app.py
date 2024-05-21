import asyncio
from app import App
from tildagonos import tildagonos
from system.eventbus import eventbus
import tildagon_hid
from events.input import Button, BUTTON_TYPES, ButtonDownEvent, ButtonUpEvent

SPECIAL_KEYS = {
    82: Button("Up", "Keyboard", BUTTON_TYPES["UP"]),
    81: Button("Down", "Keyboard", BUTTON_TYPES["DOWN"]),
    80: Button("Left", "Keyboard", BUTTON_TYPES["LEFT"]),
    79: Button("Right", "Keyboard", BUTTON_TYPES["RIGHT"]),
    40: Button("Enter", "Keyboard", BUTTON_TYPES["CONFIRM"])
}

# using an instance method wasn't working as a callback
# perhaps if we make this a classmethod it would be callable from C?
def kb_cb(unused):
    x = tildagon_hid.get_kb_event()
    while (x != None):
        print(f"Key {x.key}, mod {x.mod}, release {x.release}")
        if x.key in SPECIAL_KEYS:
            if x.release:
                eventbus.emit(ButtonUpEvent(button=SPECIAL_KEYS[x.key]))
            else:
                eventbus.emit(ButtonDownEvent(button=SPECIAL_KEYS[x.key]))
        x = tildagon_hid.get_kb_event()

class USBHostSystem(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tildagon_hid.set_kb_cb(kb_cb)

        tildagonos.set_egpio_pin((0x59, 0, (3 << 4)), 1)

