import asyncio
import display
import sys
import time

from perf_timer import PerfTimer
from system.eventbus import eventbus
from system.scheduler.events import (
    RequestForegroundPushEvent,
    RequestForegroundPopEvent,
    RequestStartAppEvent,
    RequestStopAppEvent,
)
from system.notification.events import ShowNotificationEvent


class _Scheduler:
    # Always receive all events
    _focused = True

    def __init__(self):
        # All currently running apps
        self.apps = []

        # Background tasks, always running
        self.background_tasks = {}

        # Foreground tasks, only active when the app is foregrounded
        self.update_tasks = {}

        # Apps to render
        # The app on top is focused
        self.foreground_stack = []

        # Separate stack of apps to always draw on top (for notifications etc.)
        # These apps can't have focus though
        self.on_top_stack = []

        self.last_render_time = time.ticks_us()
        self.last_update_times = []

        # To avoid re-rendering when not needed
        self.render_needed = asyncio.Event()

        # Bg/fg management events
        eventbus.on_async(
            RequestForegroundPushEvent, self._handle_request_foreground_push, self
        )
        eventbus.on_async(
            RequestForegroundPopEvent, self._handle_request_foreground_pop, self
        )

        eventbus.on_async(RequestStartAppEvent, self._handle_start_app, self)
        eventbus.on_async(RequestStopAppEvent, self._handle_stop_app, self)

    async def _handle_start_app(self, event: RequestStartAppEvent):
        self.start_app(event.app, event.foreground)
        await self.start_update_tasks(event.app)

    def start_app(self, app, foreground=False, always_on_top=False):
        self.apps.append(app)
        self.last_update_times.append(time.ticks_us())

        if foreground:
            self.foreground_stack.append(app)

        if always_on_top:
            self.on_top_stack.append(app)

        self.mark_focused()

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
            print("Stopping background", app)
            del self.background_tasks[app]
        except KeyError:
            pass

        try:
            self.update_tasks[app].cancel()
            print("Stopping ", app)
            del self.update_tasks[app]
        except KeyError:
            pass

        del self.apps[app_idx]
        del self.last_update_times[app_idx]

        eventbus.deregister(app)
        self.mark_focused()

    def app_is_foregrounded(self, app):
        return self.app_is_focused(app) or app in self.on_top_stack

    def app_is_focused(self, app):
        return self.foreground_stack and app == self.foreground_stack[-1]

    def mark_focused(self):
        for app in self.apps:
            app._focused = self.app_is_focused(app)
            app._foreground = self.app_is_foregrounded(app)

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

        self.mark_focused()

    async def _handle_request_foreground_pop(self, event):
        app = event.app

        if app not in self.apps:
            print(f"Background request ignored for app that's not running: {app}")
            return

        if app in self.foreground_stack:
            self.foreground_stack.reverse()
            self.foreground_stack.remove(app)
            self.foreground_stack.reverse()

        self.mark_focused()

    async def _handle_start_bg_task(self, event):
        if event.app not in self.background_tasks:
            await self.start_update_tasks(event.app)

    async def start_update_tasks(self, app):
        try:
            self.background_tasks[app] = asyncio.create_task(app.background_task())
        except AttributeError:
            pass

        async def mark_update_finished():
            # Unblock renderer
            self.render_needed.set()
            await asyncio.sleep(0.05)

            # If we're no longer foregounded, wait until it is before returning
            did_lose_focus = False
            while not self.app_is_foregrounded(app):
                did_lose_focus = True
                await asyncio.sleep(0.250)

            # Return control to the update task
            return did_lose_focus

        async def app_wrapper():
            try:
                await app.run(mark_update_finished)
            except Exception as e:
                sys.print_exception(e, sys.stderr)
                eventbus.emit(RequestStopAppEvent(app=app))
                eventbus.emit(
                    ShowNotificationEvent(
                        message=f"{app.__class__.__name__} has crashed"
                    )
                )

        self.update_tasks[app] = asyncio.create_task(app_wrapper())

    """async def report_errors(self):
        from system.notification.events import ShowNotificationEvent
        while True:
            tasks = tuple(self.background_tasks.items())
            for app, task in tasks:
                if task._exception:
                    print("----"*20)
                    print(task._exception)
                    task.print_stack()
                    print(app)
                    print("----"*20)
                    self.stop_app(app)
                    eventbus.emit(ShowNotificationEvent(message=f"{app.__class__.__name__} has crashed", port=3))
            await asyncio.sleep(1)"""

    async def _render_task(self):
        while True:
            # Do not bother re-rendering unless an update has happened
            await self.render_needed.wait()
            self.render_needed.clear()

            with PerfTimer("render"):
                ctx = display.start_frame()
                for app in self.foreground_stack[-1:] + self.on_top_stack:
                    with PerfTimer(f"rendering {app}"):
                        ctx.save()
                        try:
                            app.draw(ctx)
                        except Exception as e:
                            eventbus.emit(RequestStopAppEvent(app=app))
                            sys.print_exception(e, sys.stderr)
                            eventbus.emit(
                                ShowNotificationEvent(
                                    message=f"{app.__class__.__name__} has crashed"
                                )
                            )
                        ctx.restore()
                display.end_frame(ctx)
            await asyncio.sleep(0)

    async def _main(self):
        update_tasks = []
        for app in self.apps:
            update_tasks.append(self.start_update_tasks(app))
        render_task = self._render_task()
        event_task = eventbus.run()
        await asyncio.gather(render_task, event_task, *update_tasks)

    def run_forever(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._main())

    def run_for(self, time_s):
        loop = asyncio.get_event_loop()

        async def run():
            await asyncio.wait_for(self._main(), time_s)

        loop.run_until_complete(run())


scheduler = _Scheduler()
