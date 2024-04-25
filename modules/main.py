from tildagonos import tildagonos
from system.scheduler import scheduler
from system.hexpansion.app import HexpansionManagerApp

from apps.intro_app import IntroApp
import asyncio
import display

display.gfx_init()

n = tildagonos()

def startup():
    scheduler.start_app(HexpansionManagerApp(tildagonos=n))
    scheduler.start_app(IntroApp(text="EMF Camp", n_hexagons=5), foreground=True)

scheduler.run_forever(startup=startup)
