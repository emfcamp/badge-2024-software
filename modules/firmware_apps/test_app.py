from app_components.dialog import YesNoDialog


class TestApp:
    def __init__(self):
        self.dialog = YesNoDialog(
            message="Party?",
            on_yes=self._handle_party,
            on_no=self._handle_no_party,
            app=self,
        )

    def update(self, delta):
        return True

    def draw_background(self, ctx):
        ctx.gray(0).rectangle(-120, -120, 240, 240).fill()

    def draw(self, ctx):
        self.draw_background(ctx)
        ctx.rgb(0, 0, 1).rectangle(-15, -15, 30, 30).fill()
        ctx.rgba(1, 0, 0, 0.2).arc(0, 0, 100, 0, 6.4, 0).fill()
        ctx.font_size = 20
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        text_height = ctx.font_size
        ctx.rgb(1, 0, 1).move_to(0, 0).text("ASDFASDFASDFASDF").move_to(
            0, text_height
        ).text("ASDFASSSDFSDF")

    def _handle_party(self):
        print("Yay!!")

    def _handle_no_party(self):
        print("Aww :(")
