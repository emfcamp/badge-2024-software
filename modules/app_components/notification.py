<<<<<<< Updated upstream
||||||| Stash base

=======
from .tokens import label_font_size, set_color


>>>>>>> Stashed changes
class Notification:
    _half_hex_rotation = (2 * 3.141593) / 12

    def __init__(self, message, port=0, open=True):
        self.message = message
        self._open = open
        self._port = port

        self._animation_state = 0
        self._animation_target = 1 if open else 0
        self._open_time = 0
        self._close_after = 1000 * 3

    def __repr__(self):
        return f"<Notification '{self.message}' on port {self._port} ({self._open} - {self._open_time})>"

    def _is_closed(self):
        return self._animation_state < 0.01

    def open(self):
        self._animation_target = 1
        self._open = True

    def close(self):
        self._open_time = 0
        self._animation_target = 0
        self._open = False

    def update(self, delta):
        delta_s = min((delta / 1000) * 5, 1)
        animation_delta = self._animation_target - self._animation_state
        animation_step = animation_delta * delta_s
        self._animation_state += animation_step

        if self._open:
            self._open_time += delta

        if self._open and self._open_time > self._close_after:
            self.close()

    def draw(self, ctx):
        if not self._is_closed():
            ctx.save()

            ctx.font_size = label_font_size
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE

            if self._port != 0:
                ctx.rotate(self._half_hex_rotation * (self._port * 2 - 1))

<<<<<<< Updated upstream
            ctx.gray(0.3).rectangle(
                -120, -150 - self._animation_state * -30, 240, 30
            ).fill()
||||||| Stash base
            ctx.gray(0.3)\
                .rectangle(-120, -150 - self._animation_state * -30, 240, 30)\
                .fill()
=======
            set_color(ctx, "mid_green")
            ctx.rectangle(-120, -150 - self._animation_state * -30, 240, 30).fill()
>>>>>>> Stashed changes

            if self._port != 0:
                ctx.rotate(3.14)
<<<<<<< Updated upstream
                ctx.gray(1).move_to(0, 135 + self._animation_state * -30).text(
                    self.message
                )
||||||| Stash base
                ctx.gray(1) \
                    .move_to(0, 135 + self._animation_state * -30) \
                    .text(self.message)
=======
                set_color(ctx, "label")
                ctx.move_to(0, 135 + self._animation_state * -30).text(self.message)
>>>>>>> Stashed changes
            else:
<<<<<<< Updated upstream
                ctx.gray(1).move_to(0, -130 - self._animation_state * -30).text(
                    self.message
                )
||||||| Stash base
                ctx.gray(1)\
                    .move_to(0, -130 - self._animation_state * -30)\
                    .text(self.message)
=======
                set_color(ctx, "label")
                ctx.move_to(0, -130 - self._animation_state * -30).text(self.message)
>>>>>>> Stashed changes

            ctx.restore()
