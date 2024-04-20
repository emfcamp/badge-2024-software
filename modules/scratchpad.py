
from tildagonos import tildagonos
from scheduler import Scheduler
from apps.indicate_hexpansion import HexpansionInsertionApp
from apps.tick_app import TickApp
from apps.intro_app import IntroApp
from apps.pingpong_app import PingApp, PongApp

# import display

print("Oh hi")

n = tildagonos()
# display.gfx_init()

sc = Scheduler()

sc.start_app(HexpansionInsertionApp(tildagonos=n))
# sc.start_app(TickApp())
sc.start_app(IntroApp(text="EMF Camp", n_hexagons=10), foreground=True)

# sc.start_app(PingApp())
# sc.start_app(PongApp())
# sc.run_forever()
