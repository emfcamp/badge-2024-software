import _sim

_app_is_left = True


def get_app():
    if _app_is_left:
        return _sim.get_button_state(1)
    else:
        return _sim.get_button_state(0)


def get_os():
    if _app_is_left:
        return _sim.get_button_state(0)
    else:
        return _sim.get_button_state(1)


def app_is_left():
    return _app_is_left


def configure(left):
    global _app_is_left
    _app_is_left = left


PRESSED_LEFT = -1
PRESSED_RIGHT = 1
PRESSED_DOWN = 2
NOT_PRESSED = 0
