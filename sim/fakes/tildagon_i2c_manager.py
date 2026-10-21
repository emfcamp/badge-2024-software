"""Minimal simulator stub for the MicroPython-facing i2c manager API.

This only needs to satisfy imports and basic method calls for apps that touch
``i2c_mgr`` / ``tildagon_i2c_manager`` during simulation. The real C manager is
not implemented in Python, so the host shim preserves the expected API shape and
defers to a lightweight no-op behaviour.
"""

READ = 0
WRITE = 1
CHECK = 2
OFF = 65535
MIN_PERIOD_MS = 10
STATUS_IDLE = 0
STATUS_PENDING = 1
STATUS_SUCCESS = 2
STATUS_CHECK_ABORTED = 3
STATUS_I2C_ERROR = 4


class Job:
    def __init__(self, handle=-1):
        self.handle = handle
        self._period_ms = OFF
        self._status = STATUS_IDLE

    def read_into(self, buf):
        if isinstance(buf, (bytes, bytearray)):
            return 0
        return 0

    def set_period(self, period_ms, force=False):
        if period_ms is None:
            self._period_ms = OFF
            return True
        if period_ms < MIN_PERIOD_MS or period_ms > 65534:
            raise ValueError("period must be None or 10..65534 ms")
        self._period_ms = int(period_ms)
        return True

    def get_period(self):
        return None if self._period_ms == OFF else self._period_ms

    def run_once(self):
        self._status = STATUS_SUCCESS
        return True

    def get_status(self):
        return self._status

    def irq(self, handler=None):
        self._handler = handler
        return None

    def unregister(self):
        self.handle = -1
        self._status = STATUS_IDLE
        return None


def add_job(port, addr, steps, period_ms=None, high_priority=False):
    _ = (port, addr, steps, period_ms, high_priority)
    return Job()
