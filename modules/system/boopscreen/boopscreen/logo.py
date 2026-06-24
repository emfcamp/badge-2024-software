from math import pi

from .conf import conf


class Logo:
    """The logo."""

    def __init__(self, scale=1, colour=None, opacity=1, centre=None):
        """Construct."""
        self.scale = scale
        self.colour = colour or [1, 1, 1]
        self.opacity = opacity
        self.centre = centre or (0, 0)

    def draw(self, ctx):
        """Draw."""
        self.rgba = self.colour + [self.opacity]
        ctx.rgba(*self.rgba)

        ctx.translate(*self.centre)

        for _ in range(2):
            self.circle(ctx)
            self.bars(ctx)
            self.tilde(ctx)
            ctx.rotate(pi)

        ctx.fill()

    def circle(self, ctx):
        """Draw the circle."""
        ctx.rgba(*self.rgba)
        ctx.arc(0, 0, conf["circle"]["radius"] * self.scale, pi, 0, True)

        ctx.arc(
            0,
            0,
            (conf["circle"]["radius"] - conf["circle"]["ring-width"]) * self.scale,
            0,
            pi,
            False,
        )

        ctx.close_path()

    def bars(self, ctx):
        """Draw the bars."""
        horizontal_offset = (conf["bars"]["width"] / 2) * self.scale
        vertical_offset = conf["bars"]["offset"] * self.scale
        height = (conf["bars"]["height"] + conf["bars"]["offset"]) * self.scale

        ctx.move_to(-horizontal_offset, -height)
        ctx.line_to(-horizontal_offset, -vertical_offset)
        ctx.line_to(horizontal_offset, -vertical_offset)
        ctx.line_to(horizontal_offset, -height)
        ctx.close_path()

    def tilde(self, ctx):
        """Draw the ~."""
        ctx.move_to(*scale_list(conf["tilde"]["start"], self.scale))
        ctx.quad_to(*scale_list(conf["tilde"]["top-curve"], self.scale))
        ctx.line_to(*scale_list(conf["tilde"]["mid-line"], self.scale))
        ctx.quad_to(*scale_list(conf["tilde"]["bottom-curve"], self.scale))

        ctx.close_path()

    def fade(self, amount=conf["fade-rate"]):
        """Fade."""
        self.opacity -= amount

    def faded(self, limit=0):
        """Are we faded-out?"""
        return self.opacity <= limit

    def grow(self, amount=conf["growth-rate"]):
        """Grow."""
        self.scale += amount

    def full_grown(self, limit=conf["max-scale"]):
        """Are we big?"""
        return self.scale > limit


def scale_list(items, scale):
    """Scale some numbers."""
    return [x * scale for x in items]
