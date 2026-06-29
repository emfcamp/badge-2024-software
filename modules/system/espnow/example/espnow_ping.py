import app

from events.input import Buttons, BUTTON_TYPES
from system.espnow import espnow_service
from system.espnow.events import EspNowReceiveEvent
from app_components.tokens import clear_background
import settings


class ESPNowPing(app.App):
    def __init__(self):
        self.button_states = Buttons(self)
        self.last_received = None
        self.counter = 1
        self.name = settings.get("name", "esp-now")

        # Receive ESP-NOW messages. Pass a predicate to subscribe() to filter
        # Leave predicate empty to receive all
        espnow_service.subscribe(
            handler=self._on_message,
            app=self,
            predicate=lambda e: e.msg.startswith(b"hello from"),
        )

    def _on_message(self, event: EspNowReceiveEvent):
        self.last_received = event

    def update(self, delta):
        if self.button_states.get(BUTTON_TYPES["CANCEL"]):
            self.button_states.clear()
            self.minimise()

        if self.button_states.pressed(BUTTON_TYPES["CONFIRM"]):
            espnow_service.send(
                bytes(f"hello from {self.name} {self.counter}", "ascii")
            )
            self.counter += 1

    def draw(self, ctx):
        ctx.save()
        clear_background(ctx)
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.rgb(1, 0, 0).move_to(0, -80).text(f"ch: {espnow_service.wifi_channel}")

        if self.last_received is not None:
            ctx.move_to(0, -30).text(self.last_received.mac.hex())
            ctx.move_to(0, 0).text(self.last_received.msg.decode("utf-8"))
            if self.last_received.rssi is not None:
                ctx.move_to(0, 30).text(f"{self.last_received.rssi} dBm")
                ctx.move_to(0, 60).text(f"{self.last_received.timestamp}")
            else:
                ctx.move_to(0, 30).text(f"{self.last_received.timestamp}")

        ctx.restore()


__app_export__ = ESPNowPing
