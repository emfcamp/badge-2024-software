def fill_line(ctx, text, width_for_line, font_size):
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


def wrap_text(ctx, text, font_size, width=None):
    if width is None:
        width = 200
    remaining_text = text
    lines = []
    while remaining_text:
        line, remaining_text = fill_line(ctx, remaining_text, width, font_size)
        if "\n" in line:
            lines += line.split("\n")
        else:
            lines.append(line)
    return lines
