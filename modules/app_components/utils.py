def fill_line(ctx, text, font_size, width_for_line):
    ctx.save()
    ctx.font_size = font_size
    lines = []
    line = ""
    words = text.split(" ")
    for word in words:
        remaining_word = word
        while ctx.text_width(remaining_word) > width_for_line:
            word = word[:-1]
            check_word = (line + " " + word + "-").strip()
            if ctx.text_width(check_word) <= width_for_line:
                lines.append(check_word)
                line = ""
                word = remaining_word[len(word) :]
                remaining_word = word

        new_line = line + " " + word
        if ctx.text_width(new_line) > width_for_line:
            lines.append(line.strip())
            line = word
        else:
            line = new_line.strip()
    lines.append(line)
    ctx.restore()
    return lines


def wrap_text(ctx, text, font_size=None, width=None):
    if width is None:
        width = 240
    lines = text.split("\n")
    wrapped_lines = []
    for line in lines:
        lines = fill_line(ctx, line, font_size, width)
        wrapped_lines.extend(lines)
    return wrapped_lines
