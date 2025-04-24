import display
import time

display.gfx_init()

ctx = display.start_frame()
ctx.rgb(1, 0, 0).rectangle(-120, -120, 240, 240).fill()
display.end_frame(ctx)

time.sleep(0.33)

ctx = display.start_frame()
ctx.rgb(0, 1, 0).rectangle(-120, -120, 240, 240).fill()
display.end_frame(ctx)

time.sleep(0.33)

ctx = display.start_frame()
ctx.rgb(0, 0, 1).rectangle(-120, -120, 240, 240).fill()
display.end_frame(ctx)

time.sleep(0.33)

ctx = display.start_frame()
ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
display.end_frame(ctx)
