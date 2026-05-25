# main.py -- put your code here!
from esp32 import Partition
import wifi

from system.scheduler import scheduler
from system.hexpansion.app import HexpansionManagerApp
from system.patterndisplay.app import PatternDisplay
from system.notification.app import NotificationService
from system.launcher.app import Launcher
from system.power.handler import PowerEventHandler
from system.power.app import PowerManager
from frontboards.utils import detect_frontboard
import frontboard2026

fb = detect_frontboard()

# Start front-board interface
if fb == 0x2600:
    from frontboards.twentysix import TwentyTwentySix

    frontboard2026.init()
    scheduler.start_app(TwentyTwentySix())
    print("entering 2026")
else:
    from frontboards.twentyfour import TwentyTwentyFour

    scheduler.start_app(TwentyTwentyFour())
    print("entering 2024")

# Start expansion interface
scheduler.start_app(HexpansionManagerApp())

# Start led pattern displayer app
scheduler.start_app(PatternDisplay())

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
