from app import App
import asyncio
import ntptime
import wifi
import async_helpers
from system.eventbus import eventbus
from system.scheduler.events import RequestStopAppEvent

# How often to check the WiFi connection state (seconds).
_POLL_INTERVAL = 5
# How long to wait before retrying after a failed NTP sync (seconds).
_RETRY_INTERVAL = 30


async def _noop():
    # Periodic callback required by async_helpers.unblock. The blocking
    # settime() runs on a worker thread, so there's nothing to do here.
    pass


class NTPSync(App):
    """Background service that sets the RTC from NTP once WiFi connects.

    ntptime.settime() does a blocking UDP round-trip (and can hang for its
    socket timeout on a flaky network), so it's offloaded to a worker thread
    via async_helpers.unblock to avoid stalling the event/render loop.

    Once the time has been set successfully, `time_set` is set True and the
    service removes itself from the scheduler (via RequestStopAppEvent) so it
    stops consuming any cycles until the next reboot.
    """

    def __init__(self):
        super().__init__()
        self.time_set = False

    async def background_task(self):
        while not self.time_set:
            if wifi.status():
                if await self._sync():
                    self.time_set = True
                    # Remove ourselves from the scheduler entirely; this cancels
                    # both this background task and the default update loop, so
                    # nothing keeps running until the next reboot.
                    print("NTPSync: RTC set from NTP; stopping service")
                    eventbus.emit(RequestStopAppEvent(app=self))
                    return
                # Connected but the sync failed; back off before retrying so we
                # don't hammer NTP while the connection is up.
                await asyncio.sleep(_RETRY_INTERVAL)
            else:
                await asyncio.sleep(_POLL_INTERVAL)

    async def _sync(self):
        try:
            await async_helpers.unblock(ntptime.settime, _noop)
            print("NTPSync: RTC set from NTP")
            return True
        except Exception as e:
            # settime() raises OSError on DNS failure / timeout. Don't let it
            # crash the service; just try again later.
            print("NTPSync: NTP sync failed:", e)
            return False


__app_export__ = NTPSync
