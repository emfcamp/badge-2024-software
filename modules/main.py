# main.py -- put your code here!
from esp32 import Partition
import machine
import os

from system.power.handler import PowerEventHandler
import display
import frontboards
import tildagonos


tildagonos.tildagonos.init_gpio()
display.gfx_init()


# Start front-board interface

fb_i2c = machine.I2C(0)
frontboard = 0x57 in fb_i2c.scan()
if frontboard:
    # We have a frontboard, try to mount it
    mounted = frontboards.mount_frontboard(fb_i2c)
    print(f"Frontboard mounted {mounted}")
    if not mounted or "app.mpy" not in os.listdir("/frontboard"):
        # Provision the board if not mountable
        import provision_fb

        provision_fb.populate_fb()


# Do main imports after mounting the frontboard so they can
# import the year's design tokens
from system.scheduler import scheduler  # noqa: E402
from system.hexpansion.app import HexpansionManagerApp  # noqa: E402
from system.patterndisplay.app import PatternDisplay  # noqa: E402
from system.notification.app import NotificationService  # noqa: E402
from system.launcher.app import Launcher  # noqa: E402


# Start expansion interface
scheduler.start_app(HexpansionManagerApp())

# Start led pattern displayer app
scheduler.start_app(PatternDisplay())

# Start root app
scheduler.start_app(Launcher(), foreground=True)

# Start notification handler
scheduler.start_app(NotificationService(), always_on_top=True)

PowerEventHandler.RegisterDefaultCallbacks(PowerEventHandler)

if frontboard:
    # Import the interface and start the app
    import frontboard.app

    scheduler.start_app(frontboard.app.__app_export__())


Partition.mark_app_valid_cancel_rollback()

scheduler.run_forever()
