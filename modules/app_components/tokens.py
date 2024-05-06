# Display
display_x = 240
display_y = 240
display_height_inches = 1.28
ppi = display_x / display_height_inches

# Font size
one_pt = ppi / 72
ten_pt = 10 * one_pt
twelve_pt = 12 * one_pt
eighteen_pt = 18 * one_pt
twentyfour_pt = 24 * one_pt
label_font_size = ten_pt
heading_font_size = eighteen_pt

line_height = 1.5

# Colors
colors = {
    "pale_green": (175, 201, 68),
    "mid_green": (82, 131, 41),
    "dark_green": (33, 48, 24),
    "yellow": (294, 226, 0),
    "orange": (246, 127, 2),
    "pink": (245, 80, 137),
    "blue": (46, 173, 217),
}

ui_colors = {"background": colors["dark_green"], "label": (232, 230, 227)}


def clear_background(ctx):
    ctx.rgb(*colors["dark_green"]).rectangle(-120, -120, display_x, display_y).fill()


def set_color(ctx, color):
    ctx.rgb(*ui_colors.get(color, colors.get(color, color)))
