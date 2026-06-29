STA_IF = 1
STAT_CONNECTING = 0
AP_IF = 3

AUTH_OPEN = 0
AUTH_WPA2_PSK = 3

def hostname(hostname: str) -> None:
    return


class WLAN:
    # Power management modes, mirrored from the real network.WLAN.
    PM_PERFORMANCE = 1
    PM_NONE = 0
    PM_POWERSAVE = 2

    def __init__(self, mode):
        self._channel = 1

    def active(self, active=True):
        return True

    def scan(self):
        return []

    def connect(self, ssid, key=None):
        pass

    def disconnect(self):
        pass

    def isconnected(self):
        return True

    def status(self, mode=None):
        return STAT_CONNECTING

    def config(self, *args, **kwargs):
        # Read form: config("channel") -> value
        if args:
            key = args[0]
            if key == "channel":
                return self._channel
            return None
        # Write form: config(channel=6, pm=..., essid=..., ...)
        if "channel" in kwargs:
            self._channel = kwargs["channel"]
        return None

