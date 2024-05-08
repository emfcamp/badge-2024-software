import asyncio
import app
import display
import random

from app_components.dialog import YesNoDialog


class BasicApp(app.App):
    def __init__(self):
        super().__init__()
        self.color = (1, 0, 0)

    async def run(self, render_update):
        # Render initial state
        await render_update()

        while True:
            await asyncio.sleep(2)

            # Create a yes/no dialogue, add it to the overlays
            dialog = YesNoDialog("Change the colour?", self)
            self.overlays = [dialog]
            # Wait for an answer from the dialogue, and if it was yes, randomise colour
            if await dialog.run(render_update):
                self.color = (random.random(), random.random(), random.random())

            # Remove the dialogue and re-render
            self.overlays = []
            await render_update()

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(*self.color)
        display.hexagon(ctx, 0, 0, 80)
        ctx.restore()

        self.draw_overlays(ctx)
