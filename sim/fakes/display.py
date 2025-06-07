import _sim
import time

def gfx_init():
    pass


times = []
def end_frame(ctx):
    global times
    now = time.ticks_ms()
    times.append(now)
    times = [time for time in times if time > now - 1000]
    _sim.display_update(ctx)

def start_frame():
    return _sim.start_frame()

def hexagon(ctx, x, y, dim):
    return ctx.round_rectangle(x-dim, y-dim, 2*dim, 2*dim, dim).fill()

def get_fps():
    return len(times)