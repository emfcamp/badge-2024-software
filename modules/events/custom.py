from . import Event


class CustomEvent(Event):
    __slots__ = ("type", "data", "requires_focus")

    def __init__(self, type: str, data: dict, requires_focus: bool = False):
        self.type = type
        self.data = data
        self.requires_focus = requires_focus

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __contains__(self, key):
        return key in self.data

    def __repr__(self):
        return f"<{__class__.__name__}({self.type}): {self.data}>"
