from typing import Optional

from events import Event


class EspNowReceiveEvent(Event):
    __slots__ = ("mac", "msg", "rssi", "timestamp")

    def __init__(
        self, mac: bytes, msg: bytes, rssi: Optional[int], timestamp: int
    ) -> None:
        self.mac = mac
        self.msg = msg
        self.rssi = rssi
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return (
            f"<EspNowReceiveEvent: {self.mac.hex()} "
            f"rssi={self.rssi} {len(self.msg)}B>"
        )
