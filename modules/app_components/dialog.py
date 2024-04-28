import asyncio

import display
from events.input import ButtonDownEvent, BUTTON_TYPES
from system.eventbus import eventbus


class YesNoDialog:
    def __init__(self, message, app, on_yes=None, on_no=None):
        self.open = True
        self.app = app
        self.message = message
        self.no_handler = on_no
        self.yes_handler = on_yes
        self._result = None
        eventbus.on(ButtonDownEvent, self._handle_buttondown, self.app)

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)

    async def run(self, update_complete):
        while self._result is None:
            await update_complete()
            self.update(0)
            await asyncio.sleep(0.05)
        return self._result

    def update(self, delta):
        return

    def draw_message(self, ctx):
        ctx.font_size = 20
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        text_height = ctx.font_size

        ctx.rgba(1, 1, 1, 1)
        if isinstance(self.message, list):
            for idx, line in enumerate(self.message):
                ctx.move_to(0, idx * text_height).text(line)
        else:
            ctx.move_to(0, 0).text(self.message)

    def draw(self, ctx):
        ctx.save()
        ctx.rgba(0, 0, 0, 0.5)
        display.hexagon(ctx, 0, 0, 120)

        self.draw_message(ctx)
        ctx.restore()

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES['CANCEL'] in event.button:
            self._cleanup()
            self._result = False
            if self.no_handler is not None:
                self.no_handler()

        if BUTTON_TYPES['CONFIRM'] in event.button:
            self._cleanup()
            self._result = True
            if self.yes_handler is not None:
                self.yes_handler()
            
