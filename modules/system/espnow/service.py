import asyncio
import time
from typing import Any, Awaitable, Callable, Optional

import network
from aioespnow import AIOESPNow

from app import App
from system.eventbus import eventbus
from system.espnow.events import EspNowReceiveEvent

BROADCAST_MAC = b"\xff\xff\xff\xff\xff\xff"

# ESP_ERR_ESPNOW_EXIST: returned by add_peer() when the peer is already known.
_ESP_ERR_ESPNOW_EXIST = -12395

# Message handler
EspNowHandler = Callable[[EspNowReceiveEvent], Any]
# Predicate for filtering
EspNowPredicate = Callable[[EspNowReceiveEvent], bool]


class EspNowService(App):
    """Single owner of the ESP-NOW radio.

    Receives messages asynchronously and re-emits them as EspNowReceiveEvent on
    the eventbus. Apps subscribe via subscribe() (with an optional predicate)
    and send via send()/asend()
    """

    def __init__(self) -> None:
        self.aen: Optional[AIOESPNow] = None
        self._peers: set = set()
        # Last power mode seen
        self._radio_awake: Optional[bool] = None

    @property
    def wifi_channel(self) -> Optional[int]:
        sta = network.WLAN(network.STA_IF)
        return sta.config("channel") if sta.active() else None

    def _ensure_setup(self) -> None:
        # Brings up STA interface if needed, tries not to mess with other wifi settings
        sta = network.WLAN(network.STA_IF)
        if not sta.active():
            sta.active(True)

        if self.aen is None:
            self.aen = AIOESPNow()
        if not self.aen.active():
            self.aen.active(True)
        self._ensure_peer(BROADCAST_MAC)

    def _ensure_peer(self, mac: bytes) -> None:
        if mac in self._peers:
            return
        try:
            self.aen.add_peer(mac)
        except OSError as e:
            if e.errno != _ESP_ERR_ESPNOW_EXIST:
                raise
        self._peers.add(mac)

    def _has_listeners(self) -> bool:
        # Check the eventbus to see if we have anyone listening for esp-now messages
        for registry in (eventbus.async_handlers, eventbus.handlers):
            for app_handlers in registry.values():
                if app_handlers.get(EspNowReceiveEvent):
                    return True
        return False

    def _apply_power_management(self) -> None:
        # WiFi's default PM_PERFORMANCE sleeps the radio and drops esp-now messages.
        # Use PM_NONE while anything is listening, restore power-saving when nothing is.
        sta = network.WLAN(network.STA_IF)
        if not sta.active():
            return
        awake = self._has_listeners()
        if awake != self._radio_awake:
            if awake:
                print("ESP-NOW: listener(s) present, keeping radio awake (PM_NONE)")
            else:
                print("ESP-NOW: no listeners, restoring WiFi power-saving (PM_PERFORMANCE)")
            self._radio_awake = awake
        sta.config(pm=sta.PM_NONE if awake else sta.PM_PERFORMANCE)

    def subscribe(
        self,
        handler: EspNowHandler,
        app: App,
        predicate: Optional[EspNowPredicate] = None,
    ) -> Callable[[EspNowReceiveEvent], Awaitable[None]]:
        """Deliver received messages to handler(event), sync or async.

        If predicate is given, handler only fires for events where
        predicate(event) is true (filtering on .mac/.msg/.rssi/.timestamp).

        The subscription rides on the eventbus, so scheduler.deregister(app)
        cleans it up on app shutdown. Returns the wrapped handler for manual
        eventbus.remove() if needed.
        """

        async def wrapped(event: EspNowReceiveEvent) -> None:
            if predicate is not None and not predicate(event):
                return
            result = handler(event)
            # Autodetect and handle async handlers
            if hasattr(result, "send") and hasattr(result, "throw"):
                await result

        self._ensure_setup()
        eventbus.on_async(EspNowReceiveEvent, wrapped, app)
        # Wake the radio immediately for this new listener
        self._apply_power_management()
        return wrapped

    def send(self, data: bytes, mac: bytes = BROADCAST_MAC, sync: bool = False) -> bool:
        self._ensure_setup()
        self._ensure_peer(mac)
        return self.aen.send(mac, data, sync)

    async def asend(
        self, data: bytes, mac: bytes = BROADCAST_MAC, sync: bool = False
    ) -> bool:
        self._ensure_setup()
        self._ensure_peer(mac)
        return await self.aen.asend(mac, data, sync)

    async def _reconcile_power(self) -> None:
        # Reconcilliation loop for power management
        while True:
            self._apply_power_management()
            await asyncio.sleep(10)

    async def background_task(self) -> None:
        self._ensure_setup()
        asyncio.create_task(self._reconcile_power())

        # AIOESPNow's async iterator yields (mac, msg),
        # So we have to read rssi and timestamp from the peers table
        async for mac, msg in self.aen:
            entry = self.aen.peers_table.get(mac)
            if entry is not None:
                rssi, timestamp = entry[0], entry[1]
            else:
                rssi, timestamp = None, time.ticks_ms()
            eventbus.emit(EspNowReceiveEvent(mac, msg, rssi, timestamp))
