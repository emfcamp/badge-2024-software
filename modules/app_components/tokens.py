# From https://www.emfcamp.org/about/branding

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
colors = {
    "pale_green": (175, 201, 68),
    "mid_green": (82, 131, 41),
    "dark_green": (33, 48, 24),
    "yellow": (249, 226, 0),
    "orange": (246, 127, 2),
    "pink": (245, 80, 137),
    "blue": (46, 173, 217),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
}

colors = {
    name: (c[0] / 256.0, c[1] / 256.0, c[2] / 256.0) for (name, c) in colors.items()
}

ui_colors = {
    "background": colors["dark_green"],
    "label": colors["white"],
    "button_background": colors["pale_green"],
    "button_text": colors["black"],
    "active_button_background": colors["yellow"],
    "active_button_text": colors["black"],
}


def clear_background(ctx):
    ctx.rgb(*colors["dark_green"]).rectangle(-120, -120, display_x, display_y).fill()


def set_color(ctx, color):
    ctx.rgb(*ui_colors.get(color, colors.get(color, color)))


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
