class ShowNotificationEvent:
    def __init__(self, message, port=0):
        if port < 0 or port > 6:
            raise RuntimeError("Notification port n needs to be 0>=n<=6")

        self.message = message
        self.port = port
