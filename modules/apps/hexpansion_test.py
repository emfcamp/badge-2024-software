import asyncio
from test_import import a

class HexpansionTestApp:
    def update(self, delta):
        pass

    def draw(self, ctx):
        pass

    async def background_update(self):
        while True:
            print("Hi from hexpansion B!!")
            print(f"Imported value: {a}")
            await asyncio.sleep(1)


__app_export__ = HexpansionTestApp
