STA_IF = 1
STAT_CONNECTING = 0
AP_IF = 3

def hostname(hostname: str) -> None:
    return


class WLAN:
    def __init__(self, mode):
        pass

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

    def config(self, a):
        return None

