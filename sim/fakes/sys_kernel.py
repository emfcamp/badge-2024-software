class FakeHeapKindStats:
    def __init__(self, kind):
        self.kind = kind
        self.total_free_bytes = 1337
        self.total_allocated_bytes = 1337
        self.largest_free_block = 1337


class FakeHeapStats:
    general = FakeHeapKindStats("general")
    dma = FakeHeapKindStats("dma")


def heap_stats():
    return FakeHeapStats()


def usb_connected():
    return True


def usb_console_active():
    return True


def freertos_sleep(ms):
    import time

    time.sleep(ms / 1000.0)


def i2c_scan():
    return [16, 44, 45, 85, 109, 110]


def battery_charging():
    return True


def firmware_version():
    return "v0-dev"


def hardware_version():
    return "simulator"


class FakeSchedulerSnapshot:
    def __init__(self):
        self.tasks = []


def scheduler_snapshot():
    return FakeSchedulerSnapshot()
