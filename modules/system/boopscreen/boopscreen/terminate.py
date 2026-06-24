from system.eventbus import eventbus
from system.scheduler.events import RequestStopAppEvent


def terminate(app):
    """Quit the app."""
    eventbus.emit(RequestStopAppEvent(app))
