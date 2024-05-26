import asyncio
import time

from system.eventbus import eventbus


class PingEvent:
    def __init__(self):
        pass

    def __str__(self):
        return "ping"


class PongEvent:
    def __init__(self):
        pass

    def __str__(self):
        return "pong"


class PingApp:
    def __init__(self):
        self.time_since_received = None

        eventbus.on_async(PongEvent, self.respond, self)
        eventbus.on(PongEvent, self.mark_time_received, self)

        self.has_served = False

    def mark_time_received(self, event):
        self.time_since_received = time.ticks_ms()

    def update(self, delta):
        if not self.has_served:
            eventbus.emit(PingEvent())
            self.has_served = True

        if self.time_since_received is not None:
            cur_time = time.ticks_ms()
            delta = time.ticks_diff(cur_time, self.time_since_received)
            if delta > 1000:
                print("sync pong")
                self.time_since_received = None
        return True

    def draw(self, ctx):
        pass

    async def respond(self, event):
        await asyncio.sleep(1)
        print("async", str(event))
        await eventbus.emit_async(PingEvent())


class PongApp:
    def __init__(self):
        self.time_since_received = None

        eventbus.on_async(PingEvent, self.respond, self)
        eventbus.on(PingEvent, self.mark_time_received, self)

    def mark_time_received(self, event):
        self.time_since_received = time.ticks_ms()

    def update(self, delta):
        if self.time_since_received is not None:
            cur_time = time.ticks_ms()
            delta = time.ticks_diff(cur_time, self.time_since_received)
            if delta > 1000:
                print("sync ping")
                self.time_since_received = None
        return True

    def draw(self, ctx):
        pass

    async def respond(self, event):
        await asyncio.sleep(1)
        print("async", str(event))
        await eventbus.emit_async(PongEvent())
