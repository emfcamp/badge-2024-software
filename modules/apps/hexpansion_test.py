import asyncio

from app import App


class HexpansionTestApp(App):
    def __init__(self, config):
        self.config = config
        super().__init__()

    async def background_task(self):
        while True:
            print(f"Hi from hexpansion in port {self.config.port}!!")
            await asyncio.sleep(1)


__app_export__ = HexpansionTestApp
