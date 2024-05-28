import settings
import app
from app_components import layout, tokens
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from system.scheduler.events import RequestForegroundPushEvent


def string_formatter(value):
    if value is None:
        return "Default"
    else:
        return str(value)


class SettingsApp(app.App):
    def __init__(self):
        self.layout = layout.LinearLayout(items=[])
        self.make_layout_children()
        eventbus.on_async(ButtonDownEvent, self._button_handler, self)
        eventbus.on(RequestForegroundPushEvent, self.make_layout_children, self)

    async def _button_handler(self, event):
        layout_handled = await self.layout.button_event(event)
        if not layout_handled:
            if BUTTON_TYPES["CANCEL"] in event.button:
                self.minimise()

    def make_layout_children(self, event=None):
        self.layout.items = []
        for id, label, formatter in self.settings_options():
            value = settings.get(id)
            self.layout.items.append(layout.DefinitionDisplay(label, formatter(value)))

    def settings_options(self):
        return [
            ("name", "Name", string_formatter),
            ("pattern", "LED Pattern", string_formatter),
            ("wifi_tx_power", "WiFi TX power", string_formatter),
            ("wifi_connection_timeout", "WiFi connection timeout", string_formatter),
            ("wifi_ssid", "WiFi SSID", string_formatter),
            ("wifi_password", "WiFi password", string_formatter),
            ("wifi_wpa2ent_username", "WPA2 Enterprise Username", string_formatter),
        ]

    def update(self, delta):
        return True

    def draw(self, ctx):
        tokens.clear_background(ctx)
        self.layout.draw(ctx)
