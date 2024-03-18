# main.py -- put your code here!

from tildagonos import tildagonos

import gc9a01py as gc
import vga2_bold_16x16 as font
import time

n = tildagonos()

n.init_display()
n.tft.fill(gc.WHITE)

s = "@thinkl33t"

w = len(s) * 16

n.tft.text(font, s, int(120-(w/2)), int(120-(16/2)), gc.BLACK, gc.WHITE)

for r in [2, 3, 0, 1, 2]:
    n.tft.rotation(r)
    n.tft.fill(gc.WHITE)
    n.tft.text(font, s, int(120-(w/2)), int(120-(16/2)), gc.BLACK, gc.WHITE)
    time.sleep(0.5)

n.indicate_hexpansion_insertion()
