# main.py -- put your code here!

from tildagonos import tildagonos
from scheduler import scheduler as sc
from apps.indicate_hexpansion import HexpansionInsertionApp
from apps.tick_app import TickApp
from apps.intro_app import IntroApp

import display
display.gfx_init()

print("Oh hi from main!")


n = tildagonos()

# sc = Scheduler()
sc.start_app(HexpansionInsertionApp(tildagonos=n, autolaunch=False))
# sc.start_app(TickApp())
sc.start_app(IntroApp(text="EMF Camp", n_hexagons=5), foreground=True)

# To mount the eeproms. Hacky I guess lol
try:
    sc.run_for(0.5)
except Exception:
    pass

# sc.run_forever()