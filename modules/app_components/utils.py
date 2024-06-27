def fill_line(ctx, text, font_size, width_for_line):
    ctx.save()
    ctx.font_size = font_size
    extra_text = ""
    text_that_fits = text
    text_width = ctx.text_width(text_that_fits)
    while text_width > width_for_line:
        character = text_that_fits[-1]
        text_that_fits = text_that_fits[:-1]
        extra_text = character + extra_text
        text_width = ctx.text_width(text_that_fits)
    ctx.restore()
    return text_that_fits, extra_text


def wrap_text(ctx, text, font_size=None, width=None):
    if width is None:
        width = 240
    lines = text.split("\n")
    wrapped_lines = []
    for line in lines:
        lines = fill_line(ctx, line, font_size, width)
        wrapped_lines.extend(lines)
    print(wrapped_lines)
    return wrapped_lines
