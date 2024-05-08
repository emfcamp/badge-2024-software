from system.eventbus import eventbus
from events import Event


class Button:
    __slots__ = ("name", "group", "parent")

    def __init__(self, name, group, parent=None):
        self.name = name
        self.group = group
        self.parent = parent

    def __hash__(self):
        return hash((self.name, self.group))

    def _inner_repr(self):
        parents_clause = (
            f" - {self.parent._inner_repr()}" if self.parent is not None else ""
        )
        return f"{self.group}.{self.name}{parents_clause}"

    def __repr__(self):
        return f"({self._inner_repr()})"

    def __eq__(self, other):
        return self.name == other.name and self.group == other.group

    def __contains__(self, other):
        parent = self.parent
        while parent is not None:
            if other == parent:
                return True
            else:
                parent = parent.parent
        return False


BUTTON_TYPES = {
    "UNDEFINED": Button("UNDEFINED", "System"),
    "CANCEL": Button("CANCEL", "System"),
    "CONFIRM": Button("CONFIRM", "System"),
    "UP": Button("UP", "System"),
    "DOWN": Button("DOWN", "System"),
    "LEFT": Button("LEFT", "System"),
    "RIGHT": Button("RIGHT", "System"),
}


class InputEvent(Event):
    requires_focus = True


class ButtonDownEvent(InputEvent):
    __slots__ = ("button",)

    def __init__(self, button):
        self.button = button

    def __repr__(self):
        return f"<{__class__.__name__}: {repr(self.button)}>"


class ButtonUpEvent(InputEvent):
    __slots__ = ("button",)

    def __init__(self, button):
        self.button = button

    def __repr__(self):
        return f"<{__class__.__name__}: {repr(self.button)}>"


class Buttons:
    __slots__ = ("buttons",)

    def __init__(self, app):
        self.buttons = {}
        eventbus.on(ButtonDownEvent, self.handle_button_down, app)
        eventbus.on(ButtonUpEvent, self.handle_button_up, app)

    def handle_button_down(self, event: ButtonDownEvent):
        self.buttons[event.button] = True

    def handle_button_up(self, event: ButtonUpEvent):
        self.buttons[event.button] = False

    def __getitem__(self, item):
        return self.buttons[item]

    def __iter__(self):
        return self.buttons.__iter__()

    def get(self, button, default=None):
        matching_values = [
            value for (b, value) in self.buttons.items() if b == button or button in b
        ]
        return any(matching_values)

    def clear(self):
        self.buttons.clear()

    def __repr__(self):
        return f"<Buttons {self.buttons}>"
