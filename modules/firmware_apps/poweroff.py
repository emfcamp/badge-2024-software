import app
from app_components.tokens import clear_background
from app_components.dialog import YesNoDialog


class PowerOff(app.App):
    def __init__(self):
        super().__init__()
        self.off = False

    async def run(self, render_update):
        while not self.off:
            # Render initial state
            await render_update()

            # Create a yes/no dialogue, add it to the overlays
            dialog = YesNoDialog("Power off?", self)

            # Wait for an answer from the dialogue, and if it was yes, randomise colour
            if await dialog.run(render_update):
                import machine
                import bq25895

                bq25895.bq25895(machine.I2C(7)).disconnect_battery()
                self.off = True
            else:
                self.minimise()

            await render_update()

    def draw(self, ctx):
        ctx.save()
        clear_background(ctx)
        ctx.restore()

        self.draw_overlays(ctx)
