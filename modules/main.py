# main.py -- put your code here!

from system.scheduler import scheduler
from system.hexpansion.app import HexpansionManagerApp
from system.patterndisplay.app import PatternDisplay
from system.notification.app import NotificationService

from apps.basic_app import BasicApp
from frontboards.twentyfour import TwentyTwentyFour

# Start front-board interface
scheduler.start_app(TwentyTwentyFour())

# Start expansion interface
scheduler.start_app(HexpansionManagerApp())

# Start led pattern displayer app
scheduler.start_app(PatternDisplay())

# Start root app
scheduler.start_app(BasicApp(), foreground=True)

# Start notification handler
scheduler.start_app(NotificationService(), always_on_top=True)

scheduler.run_forever()

