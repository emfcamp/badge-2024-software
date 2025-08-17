import app
from app_components.notification import Notification
from system.notification.events import ShowNotificationEvent
from system.eventbus import eventbus


class NotificationService(app.App):
    def __init__(self):
        super().__init__()
        eventbus.on_async(
            ShowNotificationEvent, self._handle_incoming_notification, self
        )
        self.notifications = [
            Notification(message="", port=x, open=False) for x in range(0, 7)
        ]

    async def _handle_incoming_notification(self, event: ShowNotificationEvent):
        self.notifications[event.port].message = event.message
        self.notifications[event.port].open()

    def update(self, delta):
        for notification in self.notifications:
            try:
                notification.update(delta)
            except Exception as e:
                print(e)
                continue
        return any(notification._open for notification in self.notifications)

    def draw(self, ctx):
        for notification in self.notifications:
            notification.draw(ctx)
