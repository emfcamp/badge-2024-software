from machine import Pin, I2C, SPI
import neopixel, time
from _sim import _sim
import leds
import sys_display

BUS_SYSTEM=7
BUS_TOP=0
EPIN_LED_POWER=(0x5a, 0, (1<<2))
EPIN_ND_A=(0x5a, 1, (1<<4))
EPIN_ND_B=(0x5a, 1, (1<<5))
EPIN_ND_C=(0x59, 1, (1<<0))
EPIN_ND_D=(0x59, 1, (1<<1))
EPIN_ND_E=(0x59, 1, (1<<2))
EPIN_ND_F=(0x59, 1, (1<<3))
EPIN_BTN_1=(0x5a, 0, (1<<6))
EPIN_BTN_2=(0x5a, 0, (1<<7))
EPIN_BTN_3=(0x59, 0, (1<<0))
EPIN_BTN_4=(0x59, 0, (1<<1))
EPIN_BTN_5=(0x59, 0, (1<<2))
EPIN_BTN_6=(0x59, 0, (1<<3))
led_colours=[
    (255, 0, 0),
    (255, 255, 0),
    (0, 255, 0),
    (0, 255, 255),
    (0, 0, 255),
    (255, 0, 255),    
]

class _tildagonos:
    
    leds = neopixel.NeoPixel()
    
    def __init__(self):
        pass
        
    def init_gpio(self):
        print(
            "Warning init_gpio has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )
        
    def set_egpio_pin(self, pin, state):
        print(
            "Warning init_gpio has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )
        
    def read_egpios(self):
        print(
            "Warning init_gpio has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )
        
    def check_egpio_state(self, pin, readgpios=True):
        print(
            "Warning init_gpio has been depriciated use system.hexpansion.config HexpansionConfig or tildagon Pin instead"
        )

        return 1
    
    def set_led_power(self, state):
        pass
    
    def indicate_hexpansion_insertion(self):
        r = 0
        g = 0
        b = 255
        while True:
            ctx = sys_display.ctx(0)
            print('x')
            leds.set_all_rgb(r, g, b)
            time.sleep_ms(250)
            r, b = b, r
            leds.update()
            sys_display.update(ctx)
            
    def sel_i2c_bus(self, bus=None):
        pass

tildagonos = _tildagonos()