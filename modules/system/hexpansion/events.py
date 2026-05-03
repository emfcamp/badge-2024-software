from events import Event


class HexpansionEvent(Event):
    def __init__(self, port):
        self.port = port


class HexpansionInsertionEvent(HexpansionEvent):
    def __str__(self):
        return f"Hexpansion inserted in port: {self.port}"


class HexpansionRemovalEvent(HexpansionEvent):
    def __str__(self):
        return f"Hexpansion removed from port: {self.port}"


class HexpansionFormattedEvent(HexpansionEvent):
    def __str__(self):
        return f"Hexpansion in port {self.port} formatted"


class HexpansionMountedEvent(HexpansionEvent):
    def __init__(self, port, header=None):
        self.port = port
        self.header = header

    def __str__(self):
        return f"Hexpansion in port {self.port} mounted"


class HexpansionUnmountedEvent(HexpansionEvent):
    def __init__(self, port, header=None):
        self.port = port
        self.header = header

    def __str__(self):
        return f"Hexpansion in port {self.port} unmounted"
