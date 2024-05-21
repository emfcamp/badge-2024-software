# main.py -- put your code here!

from system.scheduler import scheduler
from system.hexpansion.app import HexpansionManagerApp
from system.patterndisplay.app import PatternDisplay
from system.notification.app import NotificationService
from system.launcher.app import Launcher

from frontboards.twentyfour import TwentyTwentyFour
from system.usbhost.app import USBHostSystem

# Start front-board interface
scheduler.start_app(TwentyTwentyFour())

# Start USB host subsystem
scheduler.start_app(USBHostSystem())

# Start expansion interface
scheduler.start_app(HexpansionManagerApp())

# Start led pattern displayer app
scheduler.start_app(PatternDisplay())

# Start root app
scheduler.start_app(Launcher(), foreground=True)

# Start notification handler
scheduler.start_app(NotificationService(), always_on_top=True)

scheduler.run_forever()

