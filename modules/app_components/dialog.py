import asyncio

import display
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus

from .tokens import label_font_size, set_color


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

    async def run(self, render_update):
        # Render once, when the dialogue opens
        self.app.overlays.append(self)
        await render_update()

        # Tightly loop, waiting for a result, then return it
        while self._result is None:
            await asyncio.sleep(0.05)
        self.app.overlays.pop()
        await render_update()
        return self._result

    def draw_message(self, ctx):
        ctx.font_size = label_font_size
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        text_height = ctx.font_size

        set_color(ctx, "label")

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
        if BUTTON_TYPES["CANCEL"] in event.button:
            self._cleanup()
            self._result = False
            if self.no_handler is not None:
                self.no_handler()

        if BUTTON_TYPES["CONFIRM"] in event.button:
            self._cleanup()
            self._result = True
            if self.yes_handler is not None:
                self.yes_handler()


class TextDialog:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890-=!\"£$%^&*()_+[];'#,./{}:@~<>?"

    def __init__(self, message, app, masked=False, on_complete=None, on_cancel=None):
        self.open = True
        self.app = app
        self.message = message
        self.cancel_handler = on_cancel
        self.complete_handler = on_complete
        self.masked = masked
        self.text = ""
        self.current = 0
        self._result = None
        eventbus.on(ButtonDownEvent, self._handle_buttondown, self.app)

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)

    async def run(self, render_update):
        # Render once, when the dialogue opens
        self.app.overlays.append(self)
        await render_update()

        # Tightly loop, waiting for a result, then return it
        while self._result is None:
            await render_update()
        self.app.overlays.pop()
        await render_update()
        return self._result

    def draw_message(self, ctx):
        ctx.font_size = label_font_size
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        set_color(ctx, "label")

        ctx.move_to(0, -15).text(self.message)
        ctx.move_to(0, 15).text(
            (self.text if not self.masked else ("*" * len(self.text)))
            + "["
            + self.alphabet[self.current]
            + "]"
        )

    def draw(self, ctx):
        ctx.save()
        ctx.rgba(0, 0, 0, 0.5)
        display.hexagon(ctx, 0, 0, 120)

        self.draw_message(ctx)
        ctx.restore()

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["CANCEL"] in event.button:
            self._cleanup()
            self._result = False
            if self.cancel_handler is not None:
                self.cancel_handler()

        if BUTTON_TYPES["CONFIRM"] in event.button:
            self._cleanup()
            self._result = self.text
            if self.complete_handler is not None:
                self.complete_handler()

        if BUTTON_TYPES["UP"] in event.button:
            self.current = (self.current - 1) % len(self.alphabet)

        if BUTTON_TYPES["DOWN"] in event.button:
            self.current = (self.current + 1) % len(self.alphabet)

        if BUTTON_TYPES["RIGHT"] in event.button:
            self.text += self.alphabet[self.current]

        if BUTTON_TYPES["LEFT"] in event.button:
            if len(self.text) > 0:
                self.text = self.text[:-1]
