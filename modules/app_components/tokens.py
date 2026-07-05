from frontboards.utils import detect_frontboard

fb = detect_frontboard()

if (fb & 0xFF00) == 0x2600:
    from frontboards.twentysix import TwentyTwentySix

    frontboard = TwentyTwentySix()
else:
    from frontboards.twentyfour import TwentyTwentyFour

    frontboard = TwentyTwentyFour()

# Display
display_x = 240
display_y = 240
display_height_inches = 1.28
ppi = display_x / display_height_inches

# Font size
one_pt = ppi / 72
seven_pt = 7 * one_pt
ten_pt = 10 * one_pt
twelve_pt = 12 * one_pt
fourteen_pt = 14 * one_pt
sixteen_pt = 16 * one_pt
eighteen_pt = 18 * one_pt
twentyfour_pt = 24 * one_pt
small_font_size = seven_pt
label_font_size = ten_pt
heading_font_size = eighteen_pt

line_height = 1.5

# Colors
colors = frontboard.colors
ui_colors = frontboard.ui_colors

# Menu highlight colours available to the user, in cycle order.
# Keys are stored in settings under "menu_highlight_color".
# "theme" restores the frontboard's default active_menu_item colour.
MENU_HIGHLIGHT_COLOR_NAMES = ["theme", "yellow", "pink", "white", "green", "orange", "blue"]

_MENU_HIGHLIGHT_COLORS = {
    "yellow": colors["yellow"],
    "pink": colors["pink"],
    "white": colors["white"],
    "orange": colors["orange"],
}

# green and blue differ between frontboards so we pull from their colors dict
if "pale_green" in colors:
    _MENU_HIGHLIGHT_COLORS["green"] = colors["pale_green"]
elif "green" in colors:
    _MENU_HIGHLIGHT_COLORS["green"] = colors["green"]

if "pale_blue" in colors:
    _MENU_HIGHLIGHT_COLORS["blue"] = colors["pale_blue"]
elif "blue" in colors:
    _MENU_HIGHLIGHT_COLORS["blue"] = colors["blue"]

_default_active_menu_item = ui_colors.get("active_menu_item")


def _apply_active_menu_item_color(ctx):
    import settings as _settings
    key = _settings.get("menu_highlight_color", "theme")
    if not key or key == "theme":
        color = _default_active_menu_item
        if callable(color):
            color(ctx)
        else:
            ctx.rgb(*color)
    else:
        color = _MENU_HIGHLIGHT_COLORS.get(key, _default_active_menu_item)
        ctx.rgb(*color)


# Patch ui_colors so set_color(ctx, "active_menu_item") picks up the user's choice.
# set_color calls callables with ctx directly, matching the gradient pattern.
ui_colors["active_menu_item"] = _apply_active_menu_item_color


symbols = {
    "arrows": {
        "left": "←",
        "up": "↑",
        "right": "→",
        "down": "↓",
        "left_right": "↔",
        "up_down": "↕",
        "north_west": "↖",
        "north_east": "↗",
        "south_east": "↘",
        "south_west": "↙",
    },
    "hexagons": {"outline": "⬡", "filled": "⬢"},
    "hexpansion": "⬣",
    "pointing_triangles": {"up": "▲", "right": "▶", "down": "▼", "left": "◀"},
    "keyboard": {
        "return": "⏎",
        "backspace": "␈",
        "shift": "␏",
        "square": "□",
        "triangle": "△",
        "diamond": "◇",
        "circle": "○",
        "club": "♣",
        "cross": "✕",
        "solderparty": "⭍",
    },
    "emf_logo": "",
    "shark": "ǩ",
    "duck": "⇩",
    "spider": "臩",
    "bat_open": "멺",
    "bat_closed": "멻",
}


def clear_background(ctx):
    set_color(ctx, "background")
    ctx.rectangle(-120, -120, display_x, display_y).fill()


def set_color(ctx, color):
    color = ui_colors.get(color, colors.get(color, color))
    try:
        color(ctx)
        return ctx
    except Exception:
        pass

    try:
        ctx.rgb(*color)
        return ctx
    except Exception:
        pass

    ctx.rgb(0.5, 0.5, 0.5)
    return ctx


def button_labels(
    ctx,
    up_label=None,
    down_label=None,
    left_label=None,
    right_label=None,
    cancel_label=None,
    confirm_label=None,
):
    set_color(ctx, "label")

    ctx.font_size = small_font_size
    ctx.text_align = ctx.CENTER
    ctx.text_baseline = ctx.MIDDLE
    if up_label is not None:
        ctx.move_to(0, -100).text(up_label)
    if down_label is not None:
        ctx.move_to(0, 100).text(down_label)

    ctx.text_align = ctx.RIGHT
    if right_label is not None:
        ctx.move_to(75, -75).text(right_label)
    if confirm_label is not None:
        ctx.move_to(75, 75).text(confirm_label)

    ctx.text_align = ctx.LEFT
    if cancel_label is not None:
        ctx.move_to(-75, -75).text(cancel_label)
    if left_label is not None:
        ctx.move_to(-75, 75).text(left_label)
