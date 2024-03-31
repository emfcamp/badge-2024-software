# main.py -- put your code here!

from tildagonos import tildagonos
import display
import time
import random
import math

n = tildagonos()

display.gfx_init()

s = "@thinkl33t"

for i in range(7):
    ctx = display.get_ctx().save().rgb(255,255,255).rectangle(-120, -120, 240, 240).fill()
    ctx = ctx.linear_gradient(-50,-50, 50, 50).add_stop(0.0, (1.0, 0.0, 0.0), 1.0).add_stop(0.5, (0.0, 1.0, 0.0), 1.0)
    ctx = ctx.add_stop(1.0, (0.0, 0.0, 1.0), 1.0).move_to(-70, 0).rotate(i*math.pi/3).text("EMF Camp").restore()
    display.end_frame(ctx)
    time.sleep(0.25)


def yay():
    while True:
        red = random.random()
        blue = random.random()
        green = random.random()
        size = random.randint(10, 100)
        ctx = display.get_ctx().save().rgb(red,green,blue).round_rectangle(random.randint(-120, 120), random.randint(-120, 120), size, size, size/2).fill()
        ctx = ctx.restore()
        display.end_frame(ctx)

n.indicate_hexpansion_insertion()
