
from tildagonos import tildagonos

from system.scheduler import scheduler as sc
from system.hexpansion.app import HexpansionManagerApp

from apps.tick_app import TickApp
from apps.intro_app import IntroApp
from apps.pingpong_app import PingApp, PongApp
from apps.test_app import TestApp


n = tildagonos()

sc.start_app(HexpansionManagerApp(tildagonos=n))
sc.start_app(IntroApp(text="EMF Camp", n_hexagons=2), foreground=True)


sc.run_forever()
