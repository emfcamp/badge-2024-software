from _sim import _sim
import leds

class NeoPixel:
    
    def __init__(self, *args, **kwargs):
        pass

    def write(self):
        _sim.leds_update()

    def fill(self, color):
        leds.set_all_rgb(*color)
    
    def __setitem__(self, item, value):
        leds.set_rgb(item, *value)