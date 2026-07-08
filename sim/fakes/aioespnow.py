import asyncio
import time


BROADCAST_MAC = b"\xff\xff\xff\xff\xff\xff"

_ETHER = []

_FAKE_RSSI = -42


class ESPNow:
    def __init__(self):
        self._active = False
        self._peers = {}
        self.peers_table = {}
        self.mac = bytes((0x02, 0x00, 0x00, 0x00, 0x00, len(_ETHER) + 1))
        self._rx = []
        self._rx_ready = asyncio.Event()

    def active(self, flag=None):
        if flag is None:
            return self._active
        self._active = bool(flag)
        if self._active:
            if self not in _ETHER:
                _ETHER.append(self)
        elif self in _ETHER:
            _ETHER.remove(self)
        return self._active

    def add_peer(self, mac, *args, **kwargs):
        self._peers[mac] = True

    def del_peer(self, mac):
        self._peers.pop(mac, None)

    def get_peers(self):
        return tuple(self._peers)

    def _deliver(self, sender_mac, msg):
        self.peers_table[sender_mac] = [_FAKE_RSSI, time.ticks_ms()]
        self._rx.append((sender_mac, msg))
        self._rx_ready.set()

    def send(self, mac, msg=None, sync=True):
        if not self._active:
            raise OSError("ESP-NOW not active")
        # Deliver to every active radio, including ourselves, so a single sim
        # instance still receives its own broadcasts.
        for radio in list(_ETHER):
            radio._deliver(self.mac, msg)
        return True

    def recv(self, timeout_ms=None):
        if self._rx:
            return self._rx.pop(0)
        return (None, None)

    def __aiter__(self):
        return self

    async def __anext__(self):
        while not self._rx:
            self._rx_ready.clear()
            await self._rx_ready.wait()
        return self._rx.pop(0)


class AIOESPNow(ESPNow):
    async def asend(self, mac, msg=None, sync=True):
        return self.send(mac, msg, sync)

    async def arecv(self):
        return await self.__anext__()
