import asyncio


class TickApp:
    def __init__(self):
        self.acc_time = 0
        self.tick = True

    def update(self, delta):
        self.acc_time += delta
        return True

    def draw(self, ctx):
        if self.acc_time > 1000_000:
            if self.tick:
                print("tick!")
            else:
                print("tock!")
            self.tick = not self.tick
            self.acc_time = 0

    async def background_task(self):
        while True:
            await asyncio.sleep(0.1)
            self.draw(None)
