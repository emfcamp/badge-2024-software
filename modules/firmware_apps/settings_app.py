import settings
import app
from app_components import layout, tokens, TextDialog, YesNoDialog
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from system.scheduler.events import RequestForegroundPushEvent


def string_formatter(value):
    if value is None:
        return "Default"
    else:
        return str(value)

async def string_editor(self, label, id, render_update):
    dialog = TextDialog(label, self)
    dialog._settings_id = id
    self.overlays = [dialog]

def reset_wifi_settings():
    print("RESET WIFI")
    for s in ["wifi_ssid","wifi_password", "wifi_wpa2ent_username"]:
        settings.set(s, None)


class SettingsApp(app.App):
    def __init__(self):
        self.layout = layout.LinearLayout(items=[])
        self.overlays = []
        eventbus.on_async(ButtonDownEvent, self._button_handler, self)
        #eventbus.on(RequestForegroundPushEvent, self.make_layout_children, self)



    async def _button_handler(self, event):
        if not self.overlays:
            layout_handled = await self.layout.button_event(event)
            if not layout_handled:
                if BUTTON_TYPES["CANCEL"] in event.button:
                    settings.save()
                    self.minimise()

    async def run(self, render_update):
        while True:
            self.layout.items = []
            for id, label, formatter, editor in self.settings_options():
                value = settings.get(id)
                entry = layout.DefinitionDisplay(label, formatter(value))
                if editor:
                    async def _button_event(event, self=self, id=id, label=label, editor=editor):
                        if BUTTON_TYPES["CONFIRM"] in event.button:
                            await editor(self, label, id, render_update)
                            return True
                        return False
                    entry.button_event =_button_event
                self.layout.items.append(entry)

            entry = layout.DefinitionDisplay("WLAN EMF defaults", "reset")
            async def _button_event_w(event, self=self):
                if BUTTON_TYPES["CONFIRM"] in event.button:
                    dialog = YesNoDialog("Reset WLAN settings", self)
                    dialog._settings_id = "WIFI_MAGIC"
                    self.overlays = [dialog]

                    return True
                return False
            entry.button_event =_button_event_w
            self.layout.items.append(entry)

            while True:
                await render_update()
                if self.overlays:
                        dialog = self.overlays[0]
                        result = await dialog.run(render_update)
                        if result != False: #!= because we want to allow entering empty strings
                            if dialog._settings_id == "WIFI_MAGIC":
                                reset_wifi_settings()
                            else:
                                settings.set(dialog._settings_id, result)
                        self.overlays = []
                        dialog = None
                        if result:
                            break


    def settings_options(self):
        return [
            ("name", "Name", string_formatter, string_editor),
            ("pattern", "LED Pattern", string_formatter, None),
            ("wifi_tx_power", "WiFi TX power", string_formatter, None),
            ("wifi_connection_timeout", "WiFi connection timeout", string_formatter, None),
            ("wifi_ssid", "WiFi SSID", string_formatter, string_editor),
            ("wifi_password", "WiFi password", string_formatter, string_editor),
            ("wifi_wpa2ent_username", "WPA2 Enterprise Username", string_formatter, string_editor),
        ]

    def update(self, delta):
        return True

    def draw(self, ctx):
        tokens.clear_background(ctx)
        self.layout.draw(ctx)
        self.draw_overlays(ctx)
