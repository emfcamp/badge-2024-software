from frontboards.twentyfour import TwentyTwentyFour

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
colors = TwentyTwentyFour().colors
ui_colors = TwentyTwentyFour().ui_colors

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
    "emf_logo": "",
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
    except Exception as e:
        print(color, e)

    try:
        ctx.rgb(*color)
        return ctx
    except Exception as e:
        print(color, e)

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
