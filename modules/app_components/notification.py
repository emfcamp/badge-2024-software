from .tokens import label_font_size, set_color


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
        self.width_limits = [120, 180, 220, 240, 240, 240, 180, 120]

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

    def get_text_for_line(self, ctx, text, line):
        width_for_line = 240
        if line < (len(self.width_limits)):
            width_for_line = self.width_limits[line]

        extra_text = ""
        text_that_fits = text
        text_width = ctx.text_width(text_that_fits)
        while text_width > width_for_line:
            character = text_that_fits[-1]
            text_that_fits = text_that_fits[:-1]
            extra_text = character + extra_text
            text_width = ctx.text_width(text_that_fits)
        return text_that_fits, extra_text

    def draw(self, ctx):
        if not self._is_closed():
            ctx.save()

            ctx.font_size = label_font_size
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE

            if self._port != 0:
                ctx.rotate(self._half_hex_rotation * (self._port * 2 - 1))

            lines = []
            extra_text = self.message
            line = 0
            while extra_text:
                text_that_fits, extra_text = self.get_text_for_line(
                    ctx, extra_text, line
                )
                lines.append(text_that_fits)
                line = line + 1

            set_color(ctx, "mid_green")
            ctx.rectangle(
                -120,
                -150
                - 30 * (len(lines) - 1)
                - (self._animation_state * -30 * len(lines)),
                240,
                30 * len(lines),
            ).fill()

            set_color(ctx, "label")
            for i in range(len(lines)):
                ctx.move_to(
                    0,
                    -130
                    - 30 * (len(lines) - 1)
                    - (self._animation_state * -30 * len(lines))
                    + 30 * i,
                ).text(lines[i])

            ctx.restore()
