from app_components import clear_background, tokens
from math import pi as PI


class EmfLogo:
    def __init__(self):
        pass

    def update(self, delta):
        pass

    def draw(self, ctx):
        clear_background(ctx)
        ctx.rgb(0.3, 0, 1).rectangle(-12, -120, 24, tokens.display_y).fill()
        ctx.rgb(0.3, 0, 0.5).rectangle(-10, -120, 20, tokens.display_y).fill()
        ctx.rgb(0.3, 0, 1).arc(
            0, 0, 70, 98 / 180 * PI, 82 / 180 * PI + PI, False
        ).fill()
        ctx.rgb(0.3, 0, 1).arc(
            0, 0, 70, 98 / 180 * PI + PI, 82 / 180 * PI + (2 * PI), False
        ).fill()
        ctx.rgb(0.3, 0, 0.5).arc(0, 0, 68, 0, 2 * PI, False).fill()
        ctx.rgb(0.3, 0, 1).arc(0, 0, 52, 0, 2 * PI, False).fill()
        ctx.rgb(*tokens.colors["dark_green"]).arc(0, 0, 50, 0, 2 * PI, False).fill()
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.font_size = 150
        ctx.rgb(0.3, 0, 1)
        ctx.move_to(0, 10).text("~")
        ctx.restore()


__Background__ = EmfLogo
