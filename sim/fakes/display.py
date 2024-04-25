import _sim

def gfx_init():
    pass

def end_frame(ctx):
    _sim.display_update(ctx)

def get_ctx():
    return _sim.get_ctx()

def hexagon(ctx, x, y, dim):
    return ctx.round_rectangle(x,y, dim, dim, dim).fill()