import app
from app_components.tokens import clear_background

from app_components.dialog import YesNoDialog


class PowerOff(app.App):
    async def run(self, render_update):
        # Render initial state
        await render_update()

        # Create a yes/no dialogue, add it to the overlays
        dialog = YesNoDialog("Power off?", self)
        self.overlays = [dialog]

        # Wait for an answer from the dialogue, and if it was yes, randomise colour
        if await dialog.run(render_update):
            import machine
            import bq25895

            bq25895.bq25895(machine.I2C(7)).disconnect_battery()

        # Remove the dialogue and re-render
        self.overlays = []

        while True:
            await render_update()

    def draw(self, ctx):
        ctx.save()
        clear_background(ctx)
        ctx.restore()

        self.draw_overlays(ctx)
