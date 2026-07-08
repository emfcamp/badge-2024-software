from system.eventbus import eventbus
from events import Event


class Button:
    __slots__ = ("name", "group", "parents", "_all_parents")

    def __init__(self, name, group, parent=None):
        self.name = name
        self.group = group
        if isinstance(parent, Button):
            self.parents = [parent]
        elif parent is None:
            self.parents = []
        else:
            self.parents = parent
        self._all_parents = None

    def __hash__(self):
        return hash((self.name, self.group))

    def _inner_repr(self):
        parents_clause = "".join(
            f" - {parent._inner_repr()}" if parent is not None else ""
            for parent in self.parents
        )
        return f"{self.group}.{self.name}{parents_clause}"

    def __repr__(self):
        return f"({self._inner_repr()})"

    def __eq__(self, other):
        return self.name == other.name and self.group == other.group

    @property
    def all_parents(self):
        if self._all_parents is not None:
            return self._all_parents
        self._all_parents = []
        for parent in self.parents:
            self._all_parents.append(parent)
            self._all_parents += parent.all_parents
        return self._all_parents

    def __contains__(self, other):
        if other == self:
            return True
        for parent in self.all_parents:
            if other == parent:
                return True
        return False

    def find_parent_in_group(self, group):
        if self.group == group:
            return self
        for parent in self.all_parents:
            if parent.group == group:
                return parent
        return None


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
    __slots__ = ("buttons", "_already_pressed")

    def __init__(self, app):
        self.buttons = {}
        self._already_pressed = set()
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

    def pressed(self, button):
        # Latched button read, only returns True once until it is read again and off
        is_down = self.get(button)
        if is_down and button not in self._already_pressed:
            self._already_pressed.add(button)
            return True
        if not is_down:
            self._already_pressed.discard(button)
        return False

    def clear(self):
        self.buttons.clear()
        self._already_pressed.clear()

    def __repr__(self):
        return f"<Buttons {self.buttons}>"
