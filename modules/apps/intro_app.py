import asyncio
import app
import math
import display
import random
import gc

from events.input import Buttons
from tildagonos import tildagonos, led_colours
from frontboards import twentyfour

class Hexagon:
    def __init__(self):
        self.red = random.random()
        self.blue = random.random()
        self.green = random.random()
        self.size = random.randint(10, 100)
        self.x = random.randint(-120, 120)
        self.y = random.randint(-120, 120)
        self.offset_x = 0
        self.offset_y = 0
        self.wiggle_offset_x = random.random() * 2 * math.pi
        self.wiggle_amplitude_x = random.randint(0, 3)
        self.wiggle_offset_y = random.random() * 2 * math.pi
        self.wiggle_amplitude_y = random.randint(2, 10)
        self.elapsed = 0

    def update(self, time_elapsed):
        self.offset_x = math.sin(time_elapsed + self.wiggle_offset_x) * self.wiggle_amplitude_x
        self.offset_y = math.sin(time_elapsed + self.wiggle_offset_y) * self.wiggle_amplitude_y

    def draw(self, ctx):
        ctx.rgba(self.red, self.green, self.blue, 0.2)
        display.hexagon(ctx, self.x + self.offset_x, self.y + self.offset_y, self.size)

class IntroApp(app.App):
    def __init__(self, text="EMF Camp", n_hexagons=10):
        self.text = text
        self.hexagons = [Hexagon() for _ in range(n_hexagons)]
        self.time_elapsed = 0
        self.dialog = None
        self.clockwise = True

    async def run(self, update_complete):
        """ Asynchronous loop for the foreground application only.
        Must await update_complete when a round of updates is completed, which triggers a draw operation.
        This will return False in most cases, or True if this app has just regained focus."""
        import time
        from app_components.dialog import YesNoDialog
        last_time = time.ticks_ms()
        while True:
            cur_time = time.ticks_ms()
            delta_ticks = time.ticks_diff(cur_time, last_time)
            print(cur_time)
            if random.random() < 0.005 and self.dialog is None:
                self.dialog = YesNoDialog("Spin clockwise?", self)
                self.clockwise = await self.dialog.run(update_complete)
                self.dialog = None
                cur_time = time.ticks_ms()
            self.update(delta_ticks)
            await update_complete()
            last_time = cur_time

    def update(self, delta):
        self.time_elapsed += delta / 1_000
        for hexagon in self.hexagons:
            hexagon.update(self.time_elapsed)

    def draw_background(self, ctx):
        ctx.gray(1 - min(1, self.time_elapsed)).rectangle(-120, -120, 240, 240).fill()

    def draw_text(self, ctx):
        text_width = ctx.text_width(self.text)
        text_height = ctx.font_size
        ctx.rotate((1 if self.clockwise else -1) * self.time_elapsed * math.pi / 3)\
            .linear_gradient(-50, -50, 50, 50)\
            .add_stop(0.0, (1.0, 0.0, 0.0), 1.0)\
            .add_stop(0.5, (0.0, 1.0, 0.0), 1.0) \
            .add_stop(1.0, (0.0, 0.0, 1.0), 1.0) \
            .move_to(0 - text_width / 2, text_height / 4)\
            .text(self.text)

    def draw(self, ctx):
        ctx.save()
        self.draw_background(ctx)
        for hexagon in self.hexagons:
            hexagon.draw(ctx)
        self.draw_text(ctx)
        ctx.restore()
        
        ctx.save()
        if self.dialog:
            self.dialog.draw(ctx)
        ctx.restore()

    async def background_task(self):
        print(self)
        button_states = Buttons(self)
        while True:
            await asyncio.sleep(0.05)
            
            for i, button in enumerate(twentyfour.BUTTONS.values()):
                if button_states.get(button):
                    color = led_colours[i]
                else:
                    color = (0,0,0)
                if i:
                    tildagonos.leds[i * 2] = color
                else:
                    tildagonos.leds[12] = color
                tildagonos.leds[1 + i * 2] = color
                    
            tildagonos.leds.write()
            
            print("fps:", display.get_fps(), f"mem used: {gc.mem_alloc()}, mem free:{gc.mem_free()}")
