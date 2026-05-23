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

print(hex(fb))
from system.boopscreen.app import BoopSpinner

from frontboards.twentyfour import TwentyTwentyFour

# Start front-board interface
if (fb & 0xFF00) == 0x2600:
    from frontboards.twentysix import TwentyTwentySix

    frontboard2026.init(fb)
    scheduler.start_app(TwentyTwentySix())
    print("entering 2026")
else:
    from frontboards.twentyfour import TwentyTwentyFour

    scheduler.start_app(TwentyTwentyFour())
    print("entering 2024")

# Start expansion interface
scheduler.start_app(HexpansionManagerApp())

# Start the spinning-tilde boop animation
scheduler.start_app(BoopSpinner(), always_on_top=True)

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
