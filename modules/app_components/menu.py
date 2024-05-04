from typing import Callable, Literal, Union

from app import App
from events.input import ButtonDownEvent
from system.eventbus import eventbus


class Menu:
    def __init__(
        self,
        app: App,
        menu_items: list[str] = [],
        position=0,
        select_handler: Union[Callable, None] = None,
        back_handler: Union[Callable, None] = None,
        animation_time_ms=300,
    ):
        self.menu_items = menu_items
        self.position = position
        self.select_handler = select_handler
        self.back_handler = back_handler
        self.animation_time_ms = animation_time_ms
        self.is_animating: Literal["up", "down", "none"] = "none"
        self.app = app

        eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)

    def _handle_buttondown(self, event: ButtonDownEvent):
        if event.button == 0:
            self.up_handler()
        if event.button == 3:
            self.down_handler()
        if event.button == 5:
            if self.back_handler is not None:
                self.back_handler()
        if event.button == 1:
            if self.select_handler is not None:
                self.select_handler(
                    self.menu_items[self.position % len(self.menu_items)]
                )

    def up_handler(self):
        self.position = (self.position - 1) % len(self.menu_items)

    def down_handler(self):
        self.position = (self.position + 1) % len(self.menu_items)

    def draw(self, ctx):
        # Current menu item
        ctx.font_size = 40
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        text_height = ctx.font_size
        focused_item_margin = 20
        line_height = 30

        ctx.rgb(1, 1, 1)
        ctx.move_to(0, 0).text(self.menu_items[self.position % len(self.menu_items)])

        # Previous menu items
        ctx.font_size = 20
        for i in range(1, 4):
            if (self.position - i) >= 0:
                ctx.move_to(0, -focused_item_margin + -i * line_height).text(
                    self.menu_items[self.position - i]
                )

        # Next menu items
        for i in range(1, 4):
            if (self.position + i) < len(self.menu_items):
                ctx.move_to(0, focused_item_margin + i * line_height).text(
                    self.menu_items[self.position + i]
                )
