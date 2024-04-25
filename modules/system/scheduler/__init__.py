import asyncio
import time
import display

from perf_timer import PerfTimer
import system.eventbus
from system.eventbus import eventbus
from system.scheduler.events import (RequestForegroundPushEvent,
                                     RequestForegroundPopEvent,
                                     RequestStartAppEvent,
                                     RequestStopAppEvent)


class _Scheduler:
    def __init__(self):
        # All currently running apps
        self.apps = []

        # Background tasks, running separately from the main update loop
        self.background_tasks = {}

        # Apps to render
        # The app on top is focused
        self.foreground_stack = []

        # Separate stack of apps to always draw on top (for notifications etc.)
        # These apps can't have focus though
        self.on_top_stack = []

        self.last_render_time = time.ticks_us()
        self.last_update_times = []

        # To synchronize update and render tasks
        self.sync_event = asyncio.Event()

        # Callback to populate the scheduler once started
        self.startup = None

    def loop_setup(self):
        # Bg/fg management events
        eventbus = system.eventbus._eventbus = system.eventbus._EventBus()
        eventbus.on_async(RequestForegroundPushEvent, self._handle_request_foreground_push, self)
        eventbus.on_async(RequestForegroundPopEvent, self._handle_request_foreground_pop, self)

        eventbus.on_async(RequestStartAppEvent, self._handle_start_app, self)
        eventbus.on_async(RequestStopAppEvent, self._handle_stop_app, self)

        if callable(self.startup):
            self.startup()

    async def _handle_start_app(self, event: RequestStartAppEvent):
        self.start_app(event.app, event.foreground)
        await self._start_background_tasks(event.app)

    def start_app(self, app, foreground=False, always_on_top=False):
        self.apps.append(app)
        self.last_update_times.append(time.ticks_us())

        if foreground:
            self.foreground_stack.append(app)

        if always_on_top:
            self.on_top_stack.append(app)

        self._mark_focused()


    async def _handle_stop_app(self, event: RequestStopAppEvent):
        print(f"Stopping app: {event}")
        self.stop_app(event.app)

    def stop_app(self, app):
        try:
            app_idx = self.apps.index(app)
        except ValueError:
            print(f"App not running: {app}")
            return

        try:
            self.foreground_stack.remove(app)
        except ValueError:
            pass

        try:
            self.on_top_stack.remove(app)
        except ValueError:
            pass

        try:
            self.background_tasks[app].cancel()
        except KeyError:
            pass

        del self.apps[app_idx]
        del self.last_update_times[app_idx]

        eventbus().deregister(app)

    def _mark_focused(self):
        for app in self.apps:
            app._focused = False
            app._foreground = True if app in self.foreground_stack else False
        if len(self.foreground_stack) > 0:
            self.foreground_stack[-1]._focused = True
            print(f"Focused app: {self.foreground_stack[-1]}")

    async def _handle_request_foreground_push(self, event):
        app = event.app

        if app not in self.apps:
            print(f"Foreground request ignored for app that's not running: {app}")
            return

        if app in self.foreground_stack:
            if self.foreground_stack[-1] is not app:
                app_idx = self.foreground_stack.index(app)
                del self.foreground_stack[app_idx]
                self.foreground_stack.append(app)
        else:
            self.foreground_stack.append(app)

        self._mark_focused()

    async def _handle_request_foreground_pop(self, event):
        app = event.app

        if app not in self.apps:
            print(f"Background request ignored for app that's not running: {app}")
            return

        if app in self.foreground_stack:
            self.foreground_stack.reverse()
            self.foreground_stack.remove(app)
            self.foreground_stack.reverse()

        self._mark_focused()

    async def _handle_start_bg_task(self, event):
        if event.app not in self.background_tasks:
            await self._start_background_tasks(event.app)

    async def _start_background_tasks(self, app):
        # TODO: check if this is async if possible? And more sanity checks. Maybe this is not the way to do it?
        try:
            self.background_tasks[app] = asyncio.create_task(app.background_update())
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
                for app in self.foreground_stack:
                    ctx.save()
                    app.draw(ctx)
                    ctx.restore()
                for app in self.on_top_stack:
                    ctx.save()
                    app.draw(ctx)
                    ctx.restore()
                display.end_frame(ctx)
            await asyncio.sleep(0)

    async def _main(self):
        self.loop_setup()
        for app in self.apps:
            await self._start_background_tasks(app)
        update_task = asyncio.create_task(self._update_task())
        render_task = asyncio.create_task(self._render_task())
        event_task = asyncio.create_task(eventbus().run())
        await asyncio.gather(update_task, render_task, event_task)

    def run_forever(self, startup=None):
        self.startup = startup
        asyncio.run(self._main())

    def run_for(self, time_s):
        async def run():
            await asyncio.wait_for(self._main(), time_s)

        asyncio.run(run())


scheduler = _Scheduler()
