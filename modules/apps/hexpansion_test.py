import asyncio


class HexpansionTestApp:
    def update(self, delta):
        pass

    def draw(self, ctx):
        pass

    async def background_update(self):
        while True:
            print("Hi from hexpansion B!!")
            await asyncio.sleep(1)


__app_export__ = HexpansionTestApp
