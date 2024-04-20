import asyncio
import time
import display

from perf_timer import PerfTimer
from eventbus import eventbus

class AppInfo:
    def __init__(self, app):
        self.app = app
        self.running = False
        self.last_updated = time.ticks_us()
        self.background_tasks = []


class Scheduler:
    def __init__(self):
        self.current_app = None
        self.apps = []
        self.background_tasks = []

        self.last_render_time = time.ticks_us()
        self.last_update_times = []

        self.sync_event = asyncio.Event()

    def start_app(self, app, foreground=False):
        self.apps.append(app)
        self.last_update_times.append(time.ticks_us())
        if foreground:
            self.current_app = app

    async def _start_background_tasks(self, app):
        # TODO: check if this is async if possible? And more sanity checks. Maybe this is not the way to do it?
        try:
            self.background_tasks.append(asyncio.create_task(app.background_update()))
        except AttributeError:
            pass

    async def _update_task(self):
        while True:
            with PerfTimer("updates"):
                for idx, app in enumerate(self.apps):
                    cur_time = time.ticks_us()
                    delta_time = time.ticks_diff(cur_time, self.last_update_times[idx])
                    app.update(delta_time)
                    self.last_update_times[idx] = cur_time
            self.sync_event.set()
            await asyncio.sleep(0)

    async def _render_task(self):
        while True:
            await self.sync_event.wait()
            self.sync_event.clear()
            with PerfTimer("render"):
                ctx = display.get_ctx()
                ctx.save()
                if self.current_app:
                    self.current_app.draw(ctx)
                ctx.restore()
                display.end_frame(ctx)
            await asyncio.sleep(0)

    async def _main(self):
        for app in self.apps:
            await self._start_background_tasks(app)
        update_task = asyncio.create_task(self._update_task())
        render_task = asyncio.create_task(self._render_task())
        event_task = asyncio.create_task(eventbus.run())
        await asyncio.gather(update_task, render_task, event_task)

    def run_forever(self):
        asyncio.run(self._main())

    def run_for(self, time_s):
        async def run():
            await asyncio.wait_for(self._main(), time_s)
        asyncio.run(run())
