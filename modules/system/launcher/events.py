from events import Event


class AppDirAddedNotificationEvent(Event):
    def __init__(self, path):
        self.path = path


class AppDirRemovedNotificationEvent(Event):
    def __init__(self, path):
        self.path = path


class InstallNotificationEvent(Event):
    pass
