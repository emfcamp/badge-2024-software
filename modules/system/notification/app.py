import app
from app_components.notification import Notification
from system.notification.events import ShowNotificationEvent
from system.eventbus import eventbus


def _advance_notification(notification, delta):
    try:
        notification.update(delta)
    except Exception:
        _log_notification_update_failure()
        return False
    return True


def _log_notification_update_failure():
    print("Notification update failed")


class NotificationService(app.App):
    def __init__(self):
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
        notifications = self.notifications
        has_active_notification = False
        index = 0
        while index < len(notifications):
            notification = notifications[index]
            if not notification._open and notification._animation_state == 0:
                index += 1
                continue
            if not _advance_notification(notification, delta):
                index += 1
                continue
            if notification._open or notification._animation_state != 0:
                has_active_notification = True
            index += 1
        return has_active_notification

    def draw(self, ctx):
        notifications = self.notifications
        index = 0
        while index < len(notifications):
            notification = notifications[index]
            if notification._animation_state >= 0.01:
                notification.draw(ctx)
            index += 1
