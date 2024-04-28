import asyncio
import app
import display
import random

from app_components.dialog import YesNoDialog


class BasicApp(app.App):
    def __init__(self):
        super().__init__()
        self.color = (1, 0, 0)

    async def run(self, update_complete):
        while True:
            await asyncio.sleep(2)
            dialog = YesNoDialog("Change the colour?", self)
            self.overlays = [dialog]
            if await dialog.run(update_complete):
                self.color = (random.random(), random.random(), random.random())
            self.overlays = []
            await update_complete()

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(*self.color)
        display.hexagon(ctx, 0, 0, 80)
        ctx.restore()

        self.draw_overlays(ctx)
