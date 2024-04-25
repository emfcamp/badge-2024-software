from async_queue import Queue as AsyncQueue
from perf_timer import PerfTimer
import asyncio


class _EventBus:
    def __init__(self):
        self.event_queue = AsyncQueue()
        self.handlers = {}
        self.async_handlers = {}

    def on(self, event_type, event_handler, app):
        print(f"Registered event handler for {event_type.__name__}: {app.__class__.__name__} - {event_handler.__name__}")
        if app not in self.handlers:
            self.handlers[app] = {}
        if event_type not in self.handlers[app]:
            self.handlers[app][event_type] = []
        self.handlers[app][event_type].append(event_handler)

    def on_async(self, event_type, event_handler, app):
        print(f"Registered async event handler for {event_type.__name__}: {app.__class__.__name__} - {event_handler.__name__}")
        if app not in self.async_handlers:
            self.async_handlers[app] = {}
        if event_type not in self.async_handlers[app]:
            self.async_handlers[app][event_type] = []
        self.async_handlers[app][event_type].append(event_handler)

    def emit(self, event):
        self.event_queue.put_nowait(event)

    async def emit_async(self, event):
        await self.event_queue.put(event)

    def remove(self, event_type, event_handler, app):
        if app in self.handlers:
            if event_type in self.handlers[app]:
                if event_handler in self.handlers[app][event_type]:
                    self.handlers[app][event_type].remove(event_handler)
        if app in self.async_handlers:
            if event_type in self.async_handlers[app]:
                if event_handler in self.async_handlers[app][event_type]:
                    self.async_handlers[app][event_type].remove(event_handler)

    def deregister(self, app):
        try:
            del self.handlers[app]
        except KeyError:
            pass
        try:
            del self.async_handlers[app]
        except KeyError:
            pass

    async def run(self):
        while True:
            event = await self.event_queue.get()

            requires_focus = hasattr(event, 'requires_focus') and event.requires_focus

            with PerfTimer("handle events"):
                for app in self.handlers.keys():
                    for event_type in self.handlers[app]:
                        if isinstance(event, event_type):
                            for handler in self.handlers[app][event_type]:
                                if not requires_focus or (requires_focus and app.__focused):
                                    handler(event)

                async_tasks = []
                for app in self.async_handlers.keys():
                    for event_type in self.async_handlers[app]:
                        if isinstance(event, event_type):
                            for handler in self.async_handlers[app][event_type]:
                                if not requires_focus or (requires_focus and app.__focused):
                                    async_tasks.append(asyncio.create_task(handler(event)))

            if len(async_tasks) > 0:
                await asyncio.gather(*async_tasks)
            else:
                await asyncio.sleep(0)

# This is the singleton for the eventbus, but it can't
# be instantiated until asyncio.run has been called, as that
# creates the event loop, which is needed by the bus for
# creating its interface.
# Switch it to a function, it's less efficient but it allows
# for direct imports that don't get stale
_eventbus = None
def eventbus():
    return _eventbus
