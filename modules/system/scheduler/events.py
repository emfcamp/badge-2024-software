class SchedulerEvent:
    def __init__(self, app):
        self.app = app


class RequestForegroundPushEvent(SchedulerEvent):
    def __init__(self, app, port=None):
        super().__init__(app)
        self.port = port


class RequestForegroundPopEvent(SchedulerEvent): ...


class RequestStartAppEvent(SchedulerEvent):
    def __init__(self, app, foreground=False):
        super().__init__(app)
        self.foreground = foreground


class RequestStopAppEvent(SchedulerEvent): ...
