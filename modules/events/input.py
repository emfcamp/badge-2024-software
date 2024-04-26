from system.eventbus import eventbus
class InputEvent:
    requires_focus = True

class ButtonDownEvent(InputEvent):
    def __init__(self, button):
        self.button = button

    def __str__(self):
        return f"Button down: {self.button}"

class ButtonUpEvent(InputEvent):
    def __init__(self, button):
        self.button = button

    def __str__(self):
        return f"Button up: {self.button}"

class Buttons:
    def __init__(self, app):
        self.buttons = [False] * 6
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

    def __str__(self):
        return str(self.buttons)