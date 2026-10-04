from events import Event


class AccessibilityEvent(Event):
    pass


class ReplaceAccessibilityHandlerEvent(AccessibilityEvent):
    def __init__(self, klass):
        self.klass = klass

    def __str__(self):
        return f"Replace a11y handler: {self.klass}"


ReplaceAccessibiltiyHandlerEvent = ReplaceAccessibilityHandlerEvent
