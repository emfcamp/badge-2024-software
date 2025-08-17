import _sim


def pipe_full():
    return False


def pipe_available():
    return True


def get_mode():
    return osd


def set_mode(no):
    pass


def set_default_mode(no):
    pass


def set_palette(pal):
    pass


def fb(mode):
    return (bytearray(240 * 240 * 4), 240, 240, 240 * 4)


def fps():
    return 60.0


update = _sim.display_update
start_frame = _sim.start_frame
get_overlay_ctx = _sim.get_overlay_ctx
overlay_clip = _sim.set_overlay_clip
osd = 256


def ctx(foo):
    if foo == osd:
        return _sim.get_overlay_ctx()
    return _sim.start_frame()


def set_backlight(a):
    pass


def fbconfig(a, b, c, d):
    pass


default = 0
rgb332 = 0
sepia = 0
cool = 0
low_latency = 0
direct_ctx = 0
lock = 0
EXPERIMENTAL_think_per_draw = 0
smart_redraw = 0
x2 = 0
x3 = 0
x4 = 0
bpp1 = 0
bpp2 = 0
bpp4 = 0
bpp8 = 0
bpp16 = 0
bpp24 = 0
palette = 0
