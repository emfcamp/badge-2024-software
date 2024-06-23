from events.input import BUTTON_TYPES
from . import tokens, utils


class Layoutable:
    height: int  # Available after draw

    def __init__(self):
        self.height = 0

    def draw(self, ctx, focused=False):
        return

    async def button_event(self, event):
        return False


class TextDisplay(Layoutable):
    def __init__(self, text, font_size=None, rgb=None):
        super().__init__()
        self.text = text
        if font_size is None:
            font_size = tokens.label_font_size
        self.font_size = font_size
        self.lines = None
        if rgb is None:
            rgb = tokens.ui_colors["label"]
        self.rgb = rgb

    def draw(self, ctx, focused=False):
        ctx.save()
        ctx.font_size = self.font_size
        if self.lines is None:
            self.lines = utils.wrap_text(ctx, self.text, ctx.font_size)
            self.height = len(self.lines) * ctx.font_size
        ctx.text_align = ctx.LEFT
        if self.rgb:
            ctx.rgb(*self.rgb)
        for i, line in enumerate(self.lines):
            ctx.move_to(0, i * ctx.font_size)
            ctx.text(line)
        ctx.restore()


class ButtonDisplay(Layoutable):
    def __init__(self, text, font_size=None, rgb=None, button_handler=None):
        self.text = text
        self.height = 60
        self.button_handler = button_handler

    def draw(self, ctx, focused=False):
        ctx.save()

        # Draw button
        ctx.translate(30, 0)
        ctx.scale(0.75, 0.75)
        if focused:
            bg = tokens.ui_colors["active_button_background"]
            fg = tokens.ui_colors["active_button_text"]
        else:
            bg = tokens.ui_colors["button_background"]
            fg = tokens.ui_colors["active_button_text"]
        ctx.rgb(*bg)
        ctx.round_rectangle(0, 0, tokens.display_x, 40, 30).fill()

        # Draw text
        ctx.rgb(*fg)
        ctx.move_to(120, 30)
        ctx.text_align = ctx.CENTER
        ctx.text(self.text)

        ctx.restore()

    async def button_event(self, event):
        if self.button_handler:
            return await self.button_handler(event)
        return False


class DefinitionDisplay(Layoutable):
    def __init__(self, label, value, button_handler=None):
        self.label = label
        self.value = value
        self.height = 0
        self.button_handler = button_handler

    async def button_event(self, event):
        if self.button_handler:
            return await self.button_handler(event)
        return False

    def draw(self, ctx, focused=False):
        ctx.save()
        self.height = 0

        # Draw heading
        ctx.font_size = tokens.one_pt * 8
        ctx.text_align = ctx.LEFT
        if focused:
            ctx.rgb(*tokens.colors["orange"])
        else:
            ctx.rgb(*tokens.colors["yellow"])

        # Draw label
        label_lines = utils.wrap_text(ctx, self.label, tokens.label_font_size)
        for line in label_lines:
            width = ctx.text_width(line)
            ctx.move_to(115 - width / 2, self.height)
            ctx.text(line)
            self.height += ctx.font_size

        ctx.rgb(*tokens.ui_colors["label"])

        # Draw value
        ctx.font_size = tokens.ten_pt
        value_lines = utils.wrap_text(ctx, self.value, tokens.label_font_size, 230)
        for line in value_lines:
            width = ctx.text_width(line)
            ctx.move_to(115 - width / 2, self.height)
            ctx.text(line)
            self.height += ctx.font_size

        ctx.restore()


class LinearLayout(Layoutable):
    def __init__(self, items):
        self.items = items
        self.y_offset = 120
        self.scale_factor = 0.9
        super().__init__()

    def draw(self, ctx):
        focused_child = self.centred_component()
        self.height = 0

        ctx.save()
        # Clip to the screen to be shown
        ctx.rectangle(-120, -120, 240, 240).clip()

        # Re-centre so the origin is in the top left
        # Use y_offset to move this down
        ctx.translate(-120, -120 + self.y_offset)

        # Scale to 90% and centre
        ctx.scale(self.scale_factor, self.scale_factor)
        ctx.translate(12, 0)

        # Draw each item in turn
        for item in self.items:
            item.draw(ctx, focused=item == focused_child)
            ctx.translate(0, item.height)
            self.height += item.height

        ctx.restore()

    def centred_component(self):
        cumulative_height = 0
        for item in self.items:
            cumulative_height += item.height * self.scale_factor
            if round(cumulative_height) > round(120 - self.y_offset):
                return item
        return self.items[0]

    async def button_event(self, event) -> bool:
        focused = self.centred_component()
        to_jump = min(focused.height * self.scale_factor, 60)
        if BUTTON_TYPES["UP"] in event.button:
            self.y_offset += to_jump
            if self.y_offset > 120:
                self.y_offset = 120
            return True
        elif BUTTON_TYPES["DOWN"] in event.button:
            self.y_offset -= to_jump
            if self.y_offset < 120 - self.height:
                self.y_offset = 120 - self.height
            return True
        else:
            return await focused.button_event(event)


a = """
import display, time
import app_components.layout

text = app_components.layout.TextDisplay("Lorem ipsum " + "abcde "*30)
foo = app_components.layout.ButtonDisplay("foo")
bar = app_components.layout.DefinitionDisplay("Wifi", "emfcamp")
layout = app_components.layout.LinearLayout([text, foo, bar])

ctx=display.get_ctx()
app_components.clear_background(ctx)
ctx.rgb(1,1,1)
layout.draw(ctx)
display.end_frame(ctx)
"""

"""
def scroll():
    for i in range(20):
        ctx=display.get_ctx()
        app_components.clear_background(ctx)
        ctx.rgb(1,1,1)
        layout.draw(ctx)
        display.end_frame(ctx)
        time.sleep_ms(100)
        layout.y_offset -= 10

"""
