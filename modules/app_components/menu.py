from typing import Any, Callable, Literal, Union

from app import App
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus

from .tokens import heading_font_size, label_font_size, line_height, set_color


def ease_out_quart(x):
    return 1 - pow(1 - x, 4)


class Menu:
    def __init__(
        self,
        app: App,
        menu_items: list[str] = [],
        position=0,
        select_handler: Union[Callable[[str, int], Any], None] = None,
        change_handler: Union[Callable[[str], Any], None] = None,
        back_handler: Union[Callable, None] = None,
        speed_ms=300,
        item_font_size=label_font_size,
        item_line_height=label_font_size * line_height,
        focused_item_font_size=heading_font_size,
        focused_item_margin=20,
    ):
        self.app = app
        self.menu_items = menu_items
        self.position = position
        self.select_handler = select_handler
        self.change_handler = change_handler
        self.back_handler = back_handler
        self.speed_ms = speed_ms
        self.item_font_size = item_font_size
        self.item_line_height = item_line_height
        self.focused_item_font_size = focused_item_font_size
        self.focused_item_margin = focused_item_margin
        self.focused_item_font_size_arr = []

        self.animation_time_ms = 0
        # self.is_animating: Literal["up", "down", "none"] = "none"
        self.is_animating: Literal["up", "down", "none"] = "up"

        eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["UP"] in event.button:
            self.up_handler()
            if self.change_handler is not None:
                self.change_handler(
                    self.menu_items[self.position % len(self.menu_items)]
                )
        if BUTTON_TYPES["DOWN"] in event.button:
            self.down_handler()
            if self.change_handler is not None:
                self.change_handler(
                    self.menu_items[self.position % len(self.menu_items)]
                )
        if BUTTON_TYPES["CANCEL"] in event.button:
            if self.back_handler is not None:
                self.back_handler()
        if BUTTON_TYPES["CONFIRM"] in event.button:
            if self.select_handler is not None:
                self.select_handler(
                    self.menu_items[self.position % len(self.menu_items)],
                    self.position % len(self.menu_items),
                )

    def up_handler(self):
        self.is_animating = "up"
        self.animation_time_ms = 0
        num_menu_items = len(self.menu_items)
        self.position = (
            (self.position - 1) % num_menu_items if num_menu_items > 0 else 1
        )

    def down_handler(self):
        self.is_animating = "down"
        self.animation_time_ms = 0
        num_menu_items = len(self.menu_items)
        self.position = (
            (self.position + 1) % num_menu_items if num_menu_items > 0 else 1
        )

    def _calculate_max_focussed_font_size(self, item, ctx):
        ctx.save()
        proposed_font_size = self.focused_item_font_size
        ctx.font_size = proposed_font_size
        width = ctx.text_width(item)
        while width > 230 and proposed_font_size > self.item_font_size:
            proposed_font_size = proposed_font_size - 0.125
            ctx.font_size = proposed_font_size
            width = ctx.text_width(item)
        ctx.restore()
        return proposed_font_size

    def draw(self, ctx):
        # calculate biggest font size a menu item should grow to
        if not self.focused_item_font_size_arr:
            for item in self.menu_items:
                fs = self._calculate_max_focussed_font_size(item, ctx)
                self.focused_item_font_size_arr = self.focused_item_font_size_arr + [fs]

        animation_progress = ease_out_quart(self.animation_time_ms / self.speed_ms)
        animation_direction = 1 if self.is_animating == "up" else -1

        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        set_color(ctx, "label")
        num_menu_items = len(self.menu_items)

        # Current menu item
        ctx.font_size = self.item_font_size + animation_progress * (
            self.focused_item_font_size_arr[
                self.position % num_menu_items if num_menu_items > 0 else 1
            ]
            - self.item_font_size
        )

        label = ""
        try:
            label = self.menu_items[
                self.position % num_menu_items if num_menu_items > 0 else 1
            ]
        except IndexError:
            label = "Empty Menu"
        ctx.move_to(
            0, animation_direction * -30 + animation_progress * animation_direction * 30
        ).text(label)

        # Previous menu items
        ctx.font_size = self.item_font_size
        for i in range(1, 4):
            if (self.position - i) >= 0 and len(self.menu_items):
                ctx.move_to(
                    0,
                    -self.focused_item_margin
                    + -i * self.item_line_height
                    - animation_direction * 30
                    + animation_progress * animation_direction * 30,
                ).text(self.menu_items[self.position - i])

        # Next menu items
        for i in range(1, 4):
            if (self.position + i) < len(self.menu_items):
                ctx.move_to(
                    0,
                    self.focused_item_margin
                    + i * self.item_line_height
                    - animation_direction * 30
                    + animation_progress * animation_direction * 30,
                ).text(self.menu_items[self.position + i])

    def update(self, delta):
        if self.is_animating != "none":
            self.animation_time_ms += delta
            if self.animation_time_ms > self.speed_ms:
                self.is_animating = "none"
                self.animation_time_ms = self.speed_ms
