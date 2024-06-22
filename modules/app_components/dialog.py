import asyncio

import display
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus

from .tokens import button_labels, label_font_size, set_color

SPECIAL_KEY_META = "..."
SPECIAL_KEY_DONE = "Done"
SPECIAL_KEY_BACK = "Back"
SPECIAL_KEY_CANCEL = "Cancel"
SPECIAL_KEY_BACKSPACE = "Bksp"
SPECIAL_KEY_SYMBOL = "Sym"
SPECIAL_KEY_SHIFT = "Shift"
SPECIAL_KEY_CAPS = "Caps Lock"
SPECIAL_KEY_SPACE = "Space"

LOWERCASE_ALPHABET = list("abcdefghijklmnopqrstuvwxyz")
UPPERCASE_ALPHABET = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890")
SYMBOL_ALPHABET = list("-=!\"£$%^&*()_+[];'#,./{}:@~<>?") + [SPECIAL_KEY_SPACE]


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
        button_labels(ctx, confirm_label="Yes", cancel_label="No")
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
    def __init__(self, message, app, masked=False, on_complete=None, on_cancel=None):
        self.open = True
        self.app = app
        self.message = message
        self.cancel_handler = on_cancel
        self.complete_handler = on_complete
        self.masked = masked
        self.text = ""
        self._current_alphabet = LOWERCASE_ALPHABET
        self._keys = []
        self._caps = False
        self._sym = False
        self._shift = False
        self._layer = 0
        self._result = None
        eventbus.on(ButtonDownEvent, self._handle_buttondown, self.app)
        self._update_keys()

    def _update_keys(self):
        if self._layer == -1:
            self._keys = [
                [SPECIAL_KEY_CANCEL],
                [SPECIAL_KEY_SYMBOL],
                [SPECIAL_KEY_SHIFT],
                [SPECIAL_KEY_CAPS],
                [SPECIAL_KEY_BACKSPACE],
                [SPECIAL_KEY_BACK],
            ]
            return

        buttons = 4 if self._layer == 0 else 6
        group_size = len(self._current_alphabet) // buttons

        if group_size == 0:
            group_size = 1

        self._keys = []
        for i in range(buttons):
            start_index = group_size * i
            end_index = (group_size * i) + group_size

            if i + 1 == buttons:
                end_index = len(self._current_alphabet)

            self._keys.append(self._current_alphabet[start_index:end_index])

        if self._layer == 0:
            self._keys.insert(4, [SPECIAL_KEY_META])
            self._keys.insert(2, [SPECIAL_KEY_DONE])

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
            self.text if not self.masked else ("*" * len(self.text))
        )

    def draw(self, ctx):
        ctx.save()
        ctx.rgba(0, 0, 0, 0.8)
        display.hexagon(ctx, 0, 0, 120)

        self.draw_message(ctx)
        if len(self._keys) == 6:
            button_labels(
                ctx,
                up_label="".join(self._keys[0]),
                down_label="".join(self._keys[3]),
                left_label="".join(self._keys[4]),
                right_label="".join(self._keys[1]),
                confirm_label="".join(self._keys[2]),
                cancel_label="".join(self._keys[5]),
            )

        ctx.restore()

    def _handle_buttondown(self, event: ButtonDownEvent):
        key = -1

        if BUTTON_TYPES["UP"] in event.button:
            key = 0
        elif BUTTON_TYPES["RIGHT"] in event.button:
            key = 1
        elif BUTTON_TYPES["DOWN"] in event.button:
            key = 3
        elif BUTTON_TYPES["LEFT"] in event.button:
            key = 4
        elif BUTTON_TYPES["CANCEL"] in event.button:
            key = 5
        elif BUTTON_TYPES["CONFIRM"] in event.button:
            key = 2

        if key == -1:
            return

        selected = self._keys[key]
        if len(selected) == 1:
            selected = self._keys[key][0]

            if selected == SPECIAL_KEY_SPACE:
                selected = " "

            if selected == SPECIAL_KEY_DONE:
                self._cleanup()
                self._result = self.text
                if self.complete_handler is not None:
                    self.complete_handler()
            elif selected == SPECIAL_KEY_CANCEL:
                self._cleanup()
                self._result = False
                if self.cancel_handler is not None:
                    self.cancel_handler()
            elif selected == SPECIAL_KEY_BACKSPACE:
                self.text = self.text[:-1]
            elif selected == SPECIAL_KEY_BACK:
                self._layer = 0
            elif selected == SPECIAL_KEY_META:
                self._layer = -1
            elif selected == SPECIAL_KEY_SYMBOL:
                self._layer = 0
                if self._sym:
                    self._current_alphabet = LOWERCASE_ALPHABET
                    self._sym = False
                    self._caps = False
                else:
                    self._current_alphabet = SYMBOL_ALPHABET
                    self._sym = True
            elif selected == SPECIAL_KEY_SHIFT:
                self._layer = 0
                self._shift = not self._shift
                if self._shift:
                    self._current_alphabet = UPPERCASE_ALPHABET
                else:
                    self._current_alphabet = LOWERCASE_ALPHABET
            elif selected == SPECIAL_KEY_CAPS:
                self._layer = 0
                self._caps = not self._caps
                if self._caps:
                    self._current_alphabet = UPPERCASE_ALPHABET
                else:
                    self._current_alphabet = LOWERCASE_ALPHABET
            else:
                self.text += selected
                if self._shift:
                    self._shift = False
                    self._current_alphabet = LOWERCASE_ALPHABET
                self._layer = 0
                if self._caps:
                    self._current_alphabet = UPPERCASE_ALPHABET
                else:
                    self._current_alphabet = LOWERCASE_ALPHABET
        elif len(selected) > 0:
            self._current_alphabet = selected
            self._layer = 1

        self._update_keys()
