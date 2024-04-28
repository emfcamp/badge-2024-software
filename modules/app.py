import asyncio
import time

class App:
    def __init__(self):
        self.overlays = []
        pass

    async def run(self, update_complete):
        """ Asynchronous loop for the foreground application only.
        Must await update_complete when a round of updates is completed, which triggers a draw operation.
        This will return False in most cases, or True if this app has just regained focus."""
        last_time = time.ticks_ms()
        while True:
            cur_time = time.ticks_ms()
            delta_ticks = time.ticks_diff(cur_time, last_time)
            self.update(delta_ticks)
            await update_complete()
            last_time = cur_time

    def update(self, delta):
        pass

    def draw(self, ctx):
        self.draw_overlays(ctx)
    
    def draw_overlays(self, ctx):
        for overlay in self.overlays:
            ctx.save()
            overlay.draw(ctx)
            ctx.restore()

    async def background_task(self):
        """ Asynchronous loop for all applications, regardless of if they're focused."""
        last_time = time.ticks_ms()
        while True:
            cur_time = time.ticks_ms()
            delta_ticks = time.ticks_diff(cur_time, last_time)
            self.background_update(delta_ticks)
            await asyncio.sleep(0)
            last_time = cur_time

    def background_update(self, delta):
        pass
