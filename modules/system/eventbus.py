import asyncio

from async_queue import Queue as AsyncQueue
from perf_timer import PerfTimer


class _EventBus:
    def __init__(self):
        self.event_queue = AsyncQueue()
        self.handlers = {}
        self.async_handlers = {}

    def on(self, event_type, event_handler, app):
        print(
            f"Registered event handler for {event_type.__name__}: {app.__class__.__name__} - {event_handler.__name__}"
        )
        if app not in self.handlers:
            self.handlers[app] = {}
        if event_type not in self.handlers[app]:
            self.handlers[app][event_type] = []
        self.handlers[app][event_type].append(event_handler)

    def on_async(self, event_type, event_handler, app):
        print(
            f"Registered async event handler for {event_type.__name__}: {app.__class__.__name__} - {event_handler.__name__}"
        )
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
                    print(
                        f"Removed event handler for {event_type.__name__}: {app.__class__.__name__} - {event_handler.__name__}"
                    )
                    self.handlers[app][event_type].remove(event_handler)
        if app in self.async_handlers:
            if event_type in self.async_handlers[app]:
                if event_handler in self.async_handlers[app][event_type]:
                    print(
                        f"Removed event handler for {event_type.__name__}: {app.__class__.__name__} - {event_handler.__name__}"
                    )
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
            requires_focus = hasattr(event, "requires_focus") and event.requires_focus

            # For both synchronous and asynchronous handlers, loop over the apps
            # that have registered handlers, then if the app is eligible to receive
            # the event, loop over the event types. If any match, loop over the handlers
            # and invoke.
            #
            # N.B. These loops use tuple(...) as event handlers may themselves trigger
            # new handlers to be registered. We don't make any guarantee if these handlers
            # will be invoked or not for the event that triggered their registration, but
            # we must avoid RuntimeError due to dictionary edits.
            with PerfTimer("Synchronous event handlers"):
                for app in tuple(self.handlers.keys()):
                    if getattr(app, "_focused", False) or not requires_focus:
                        for event_type in tuple(self.handlers[app]):
                            if isinstance(event, event_type):
                                for handler in tuple(self.handlers[app][event_type]):
                                    handler(event)

            async_tasks = []
            with PerfTimer("Asynchronous event handlers"):
                for app in tuple(self.async_handlers.keys()):
                    if getattr(app, "_focused", False) or not requires_focus:
                        for event_type in tuple(self.async_handlers[app]):
                            if isinstance(event, event_type):
                                for handler in tuple(
                                    self.async_handlers[app][event_type]
                                ):
                                    async_tasks.append(
                                        asyncio.create_task(handler(event))
                                    )

            if async_tasks:
                await asyncio.gather(*async_tasks)
            else:
                await asyncio.sleep(0)


eventbus = _EventBus()
eventbus = _EventBus()
