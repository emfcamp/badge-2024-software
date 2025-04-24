import settings
import app
from app_components import layout, tokens, TextDialog
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from system.patterndisplay.events import PatternReload


def string_formatter(value):
    if value is None:
        return "Default"
    else:
        return str(value)


def masked_string_formatter(value):
    if value is None:
        return "Default"
    else:
        return "*" * 8


def pct_formatter(value):
    if value is None:
        return "Default"
    else:
        return f"{value:.0%}"


def reset_wifi_settings():
    print("RESET WIFI")
    for s in ["wifi_ssid", "wifi_password", "wifi_wpa2ent_username"]:
        settings.set(s, None)


PATTERNS = ["rainbow", "cylon", "flash", "off"]
BRIGHTNESSES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


class SettingsApp(app.App):
    def __init__(self):
        super().__init__()
        self.layout = layout.LinearLayout(items=[layout.DefinitionDisplay("", "")])
        self.overlays = []
        self.dialog = None
        eventbus.on_async(ButtonDownEvent, self._button_handler, self)
        # eventbus.on(RequestForegroundPushEvent, self.make_layout_children, self)

    async def string_editor(self, label, id, render_update):
        self.dialog = TextDialog(label, self)
        self.dialog._settings_id = id

    async def masked_string_editor(self, label, id, render_update):
        self.dialog = TextDialog(label, self, masked=True)
        self.dialog._settings_id = id

    async def _button_handler(self, event):
        if not self.overlays:
            layout_handled = await self.layout.button_event(event)
            if not layout_handled:
                if BUTTON_TYPES["CANCEL"] in event.button:
                    settings.save()
                    self.minimise()
        else:
            return True

    async def update_values(self):
        for item in self.layout.items:
            if isinstance(item, layout.DefinitionDisplay):
                for id, label, formatter, editor in self.settings_options():
                    if item.label == label:
                        value = settings.get(id)
                        item.value = formatter(value)

    async def run(self, render_update):
        while True:
            self.layout.items = []
            for id, label, formatter, editor in self.settings_options():
                value = settings.get(id)
                print(editor)
                if editor:

                    async def _button_event(event, label=label, id=id, editor=editor):
                        if BUTTON_TYPES["CONFIRM"] in event.button:
                            print(f"Event: {id} - {editor}")
                            await editor(label, id, render_update)
                            return True
                        return False

                    entry = layout.DefinitionDisplay(
                        label, formatter(value), button_handler=_button_event
                    )
                else:
                    entry = layout.DefinitionDisplay(label, formatter(value))
                self.layout.items.append(entry)

                if id == "pattern":

                    async def _button_event_pattern_toggle(event):
                        print(event)
                        if BUTTON_TYPES["CONFIRM"] in event.button:
                            pattern = settings.get("pattern")
                            if not pattern:
                                pattern = "rainbow"
                            idx = PATTERNS.index(pattern) + 1
                            if idx >= len(PATTERNS):
                                idx = 0
                            print(f"{PATTERNS} {idx}")
                            settings.set("pattern", PATTERNS[idx])
                            eventbus.emit(PatternReload())
                            await self.update_values()
                            await render_update()
                            return True
                        return False

                    entry = layout.ButtonDisplay(
                        "Next pattern", button_handler=_button_event_pattern_toggle
                    )
                    self.layout.items.append(entry)

                if id == "pattern_brightness":

                    async def _button_event_pattern_toggle(event):
                        print(event)
                        if BUTTON_TYPES["CONFIRM"] in event.button:
                            bright = settings.get("pattern_brightness")
                            if not bright:
                                bright = 0.1
                            idx = BRIGHTNESSES.index(bright) + 1
                            if idx >= len(BRIGHTNESSES):
                                idx = 0
                            print(f"{BRIGHTNESSES} {idx}")
                            settings.set("pattern_brightness", BRIGHTNESSES[idx])
                            await self.update_values()
                            await render_update()
                            return True
                        return False

                    entry = layout.ButtonDisplay(
                        "Toggle", button_handler=_button_event_pattern_toggle
                    )
                    self.layout.items.append(entry)

            async def _button_event_w(event):
                print(event)
                if BUTTON_TYPES["CONFIRM"] in event.button:
                    print("wifi")
                    reset_wifi_settings()
                    print("update")
                    await self.update_values()
                    print("render")
                    await render_update()
                    return True
                return False

            entry = layout.ButtonDisplay("Reset WiFi", button_handler=_button_event_w)
            self.layout.items.append(entry)

            while True:
                await render_update()
                if self.dialog:
                    result = await self.dialog.run(render_update)
                    if (
                        result is not False
                    ):  #!= because we want to allow entering empty strings
                        settings.set(self.dialog._settings_id, result)
                    self.dialog = None
                    if result:
                        break

    def settings_options(self):
        return [
            ("name", "Name", string_formatter, self.string_editor),
            ("pattern", "LED Pattern", string_formatter, None),
            ("pattern_brightness", "Pattern brightness", pct_formatter, None),
            ("pattern_mirror_hexpansions", "Mirror pattern", string_formatter, None),
            ("update_channel", "Update channel", string_formatter, None),
            ("wifi_tx_power", "WiFi TX power", string_formatter, None),
            (
                "wifi_connection_timeout",
                "WiFi connection timeout",
                string_formatter,
                None,
            ),
            ("wifi_ssid", "WiFi SSID", string_formatter, self.string_editor),
            (
                "wifi_password",
                "WiFi password",
                masked_string_formatter,
                self.masked_string_editor,
            ),
            (
                "wifi_wpa2ent_username",
                "WPA2 Enterprise Username",
                string_formatter,
                self.string_editor,
            ),
        ]

    def update(self, delta):
        return True

    def draw(self, ctx):
        tokens.clear_background(ctx)
        self.layout.draw(ctx)
        self.draw_overlays(ctx)


__app_export__ = SettingsApp
