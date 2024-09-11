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
                import power

                power.Off()
                self.off = True
            else:
                self.minimise()

            await render_update()

    def draw(self, ctx):
        ctx.save()
        if not self.off:
            clear_background(ctx)
        if self.off:
            from egpio import ePin

            HEXPANSION_POWER = {
                (2, 12),
                (2, 13),
                (1, 8),
                (1, 9),
                (1, 10),
                (1, 11),
            }
            for epin in HEXPANSION_POWER:
                pin = ePin(epin, ePin.OUT)
                pin.on()
            pin = ePin((2, 2), ePin.OUT)
            pin.off()
            ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
            ctx.font_size = 22
            ctx.text_align = ctx.CENTER
            ctx.rgb(0.96, 0.49, 0).move_to(0, -11).text("It is now safe to unplug")
            ctx.move_to(0, 11).text("your badge.")
        ctx.restore()

        self.draw_overlays(ctx)
