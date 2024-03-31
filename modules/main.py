# main.py -- put your code here!

from tildagonos import tildagonos
import display
import time
import random
import math

n = tildagonos()

display.gfx_init()

s = "EMF Camp"

spins = 3
its = spins*6+1
for i in range(its):
    ctx = display.get_ctx().save().gray(1-(i/its)).rectangle(-120, -120, 240, 240).fill()
    s_width = ctx.text_width(s)
    s_height = ctx.font_size
    ctx = ctx.linear_gradient(-50,-50, 50, 50).add_stop(0.0, (1.0, 0.0, 0.0), 1.0).add_stop(0.5, (0.0, 1.0, 0.0), 1.0)
    ctx = ctx.add_stop(1.0, (0.0, 0.0, 1.0), 1.0).move_to(0-s_width/2, s_height/4).rotate(i*math.pi/3).text(s).restore()
    display.end_frame(ctx)
    time.sleep(0.05)


def bestagons(n):
    while n:
        red = random.random()
        blue = random.random()
        green = random.random()
        size = random.randint(10, 100)
        ctx = display.get_ctx().save().rgba(red,green,blue, 0.2)
        display.hexagon(ctx, random.randint(-120, 120), random.randint(-120, 120), size)
        ctx = ctx.restore()
        display.end_frame(ctx)
        n -= 1


bestagons(10)
n.indicate_hexpansion_insertion()
