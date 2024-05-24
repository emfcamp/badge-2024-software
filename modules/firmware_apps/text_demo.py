import app
from app_components import TextDialog, clear_background
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus


class TextDemo(app.App):
    def __init__(self):
        super().__init__()
        self.name = "world!"

    async def run(self, render_update):
        await render_update()

        dialog = TextDialog("What is your name?", self)
        self.overlays = [dialog]

        if await dialog.run(render_update):
            self.name = dialog.text

        eventbus.on(ButtonDownEvent, self._handle_buttondown, self)

        self.overlays = []
        while True:
            await render_update()

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["CANCEL"] in event.button:
            self.minimise()

    def draw(self, ctx):
        clear_background(ctx)

        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.gray(1).move_to(0, 0).text("Hello " + self.name)
        ctx.restore()

        self.draw_overlays(ctx)
