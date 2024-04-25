from system.eventbus import eventbus
from events.input import ButtonDownEvent


class YesNoDialog:
    def __init__(self, message, on_yes, on_no, app):
        self.open = True
        self.app = app
        self.message = message
        self.no_handler = on_no
        self.yes_handler = on_yes

        eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def update(self, delta):
        pass

    def draw_message(self, ctx):
        ctx.font_size = 20
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        text_height = ctx.font_size

        ctx.rgb(1, 1, 1)
        if isinstance(self.message, list):
            for idx, line in enumerate(self.message):
                ctx.move_to(0, idx * text_height).text(line)
        else:
            ctx.move_to(0, 0).text(self.message)

    def draw(self, ctx):

        ctx.rgba(1, 0, 0, 0.5).arc(0, 0, 100, 0, 6.4, 0).fill()

        # TODO: why hexagon bg no work? :(
        # ctx.rgb(1, 0, 0)
        # display.hexagon(ctx, 1, 1, 30)

        ctx.save()
        self.draw_message(ctx)
        ctx.restore()

    def _handle_buttondown(self, event: ButtonDownEvent):
        print(event)
        if event.button == 1:
            if self.no_handler is not None:
                self.no_handler()
            self._cleanup()

        if event.button == 5:
            if self.yes_handler is not None:
                self.yes_handler()
            self._cleanup()

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)
        self.open = False
