from system.notification.app import NotificationService

from system.scheduler import scheduler as sc
from system.hexpansion.app import HexpansionManagerApp

from apps.intro_app import IntroApp


sc.start_app(HexpansionManagerApp())
sc.start_app(IntroApp(text="EMF Camp", n_hexagons=0), foreground=True)
sc.start_app(NotificationService(), always_on_top=True)

sc.run_forever()
