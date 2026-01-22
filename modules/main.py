# main.py -- put your code here!
from esp32 import Partition
import wifi

from system.scheduler import scheduler
from system.hexpansion.app import HexpansionManagerApp
from system.patterndisplay.app import PatternDisplay
from system.emotebackleds.app import EmoteBackLEDs
from system.notification.app import NotificationService
from system.launcher.app import Launcher
from system.power.handler import PowerEventHandler
from system.power.app import PowerManager

from frontboards.twentyfour import TwentyTwentyFour


# Start front-board interface
scheduler.start_app(TwentyTwentyFour())

# Start expansion interface
scheduler.start_app(HexpansionManagerApp())

# Start led pattern displayer app
scheduler.start_app(PatternDisplay())

# Start back-leds emoter

scheduler.start_app(EmoteBackLEDs())

# Start root app
scheduler.start_app(Launcher(), foreground=True)

# Start notification handler
scheduler.start_app(NotificationService(), always_on_top=True)

# Start power management app
scheduler.start_app(PowerManager())

try:
    wifi.connect()
except Exception:
    pass

PowerEventHandler.RegisterDefaultCallbacks(PowerEventHandler)

Partition.mark_app_valid_cancel_rollback()

scheduler.run_forever()
