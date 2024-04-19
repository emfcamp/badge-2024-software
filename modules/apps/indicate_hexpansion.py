import asyncio

class HexpansionInsertionApp:
    def __init__(self, tildagonos):
        self.tildagonos = tildagonos

    def update(self, delta):
        pass

    def draw(self, display):
        pass

    async def background_update(self):
        await self.tildagonos.indicate_hexpansion_insertion()

