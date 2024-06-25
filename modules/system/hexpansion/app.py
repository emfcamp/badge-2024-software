import asyncio
import os

import app
from system.hexpansion.config import HexpansionConfig
from system.hexpansion.events import HexpansionRemovalEvent, HexpansionInsertionEvent
from system.hexpansion.util import (
    read_hexpansion_header,
    get_hexpansion_block_devices,
    detect_eeprom_addr,
)

from app_components.dialog import YesNoDialog
from perf_timer import PerfTimer
from system.notification.events import ShowNotificationEvent
from system.scheduler.events import (
    RequestForegroundPushEvent,
    RequestForegroundPopEvent,
    RequestStartAppEvent,
    RequestStopAppEvent,
)
from tildagonos import EPIN_ND_A, EPIN_ND_B, EPIN_ND_C, EPIN_ND_D, EPIN_ND_E, EPIN_ND_F
from tildagonos import led_colours
from tildagonos import tildagonos
from egpio import ePin
from system.eventbus import eventbus
from machine import I2C
from events.input import Buttons
import vfs
import sys
import settings


class HexpansionManagerApp(app.App):
    def __init__(self, autolaunch=True):
        super().__init__()
        eventbus.on_async(
            HexpansionInsertionEvent, self.handle_hexpansion_insertion, self
        )
        eventbus.on_async(HexpansionRemovalEvent, self.handle_hexpansion_removal, self)
        self.mountpoints = {}
        self.format_requests = []
        self.format_dialog = None
        self.format_dialog_port = None
        self.buttons = Buttons(self)
        self.hexpansion_apps = {}
        self.autolaunch = autolaunch

    def update(self, delta):
        if len(self.format_requests) > 0 and self.format_dialog is None:
            (eep, port) = self.format_requests.pop()

            def format_eep():
                self._format_eeprom(eep)
                self._mount_eeprom(eep, port)
                self.format_dialog = None
                self.format_dialog_port = None

            def close():
                self.format_dialog = None
                self.format_dialog_port = None
                eventbus.emit(RequestForegroundPopEvent(self))

            self.format_dialog = YesNoDialog(
                message=["Format", f"hexpansion {port}?"],
                on_yes=format_eep,
                on_no=close,
                app=self,
            )

            self.format_dialog_port = port

            eventbus.emit(RequestForegroundPushEvent(self))
            return True

    def draw(self, ctx):
        if self.format_dialog is not None:
            self.format_dialog.draw(ctx)

    def _cleanup_import_path(self, old_cwd, old_sys_path):
        sys.path.clear()
        for p in old_sys_path:
            sys.path.append(p)
        os.chdir(old_cwd)

    def _launch_hexpansion_app(self, port):
        if port not in self.mountpoints:
            return

        mount = self.mountpoints[port].lstrip("/")

        old_cwd = os.getcwd()
        old_sys_path = sys.path[:]

        os.chdir("/")

        if "remote" in os.listdir():
            sys.path.append("/remote")

        try:
            _package = __import__(f"{mount}.app")
            package = _package.app
            print(f"Found app package: {package}")
        except ImportError as e:
            print(e)
            print("App module not found")
            self._cleanup_import_path(old_cwd, old_sys_path)
            return

        try:
            App = package.__app_export__ if hasattr(package, "__app_export__") else None
        except ValueError as e:
            print(e)
            App = None

        if App is None:
            print("No exported app found")
            self._cleanup_import_path(old_cwd, old_sys_path)
            return
        print("Found app")

        config = HexpansionConfig(port)

        try:
            app = App(config=config)
            print("Initialized app with config")
        except TypeError as e:
            print(f"Could not pass config to app: {e}")
            app = App()

        eventbus.emit(RequestStartAppEvent(app))
        self.hexpansion_apps[port] = app

        self._cleanup_import_path(old_cwd, old_sys_path)

    def _stop_hexpansion_app(self, app, port):
        print(f"Trying to stop app: {app}")
        eventbus.emit(RequestStopAppEvent(app))
        del self.hexpansion_apps[port]

        # Clean up imported hexpansion modules
        mount = self.mountpoints[port].lstrip("/")
        for module in sys.modules.keys():
            if module.startswith(mount):
                print(f"Deleting module: {module}")
                del sys.modules[module]

    def _format_eeprom(self, eep):
        print("Formatting...")
        vfs.VfsLfs2.mkfs(eep)

    def _mount_eeprom(self, eep, port):
        mountpoint = f"/hexpansion_{port}"

        try:
            # This is mounted already, unmount first
            vfs.umount(mountpoint)
        except OSError:
            pass

        try:
            print(f"Attempting to mount i2c eeprom from hexpansion port {port}")
            vfs.mount(eep, mountpoint)
        except Exception as e:
            print(f"Failed to mount: {e}")
            # self.format_requests.append((eep, port))
            # eventbus.emit(RequestForegroundPushEvent(self))
            return

        self.mountpoints[port] = mountpoint
        print(f"Mounted eeprom to {mountpoint}")
        print("Hexpansion files:", os.listdir(mountpoint))

        if self.autolaunch:
            self._launch_hexpansion_app(port)

    async def handle_hexpansion_insertion(self, event):
        print(event)
        i2c = I2C(event.port)

        # Autodetect eeprom addr
        addr, addr_len = detect_eeprom_addr(i2c)
        if addr is None:
            print("Scan found no eeproms")
            return

        # Do we have a header?
        header = read_hexpansion_header(i2c, addr, addr_len=addr_len)
        if header is None:
            return

        if header.friendly_name != "":
            eventbus.emit(
                ShowNotificationEvent(message=header.friendly_name, port=event.port)
            )

        print("Found hexpansion header:")
        print(header)

        # Try creating block devices, one for the whole eeprom,
        # one for the partition with the filesystem on it
        try:
            eep, partition = get_hexpansion_block_devices(
                i2c, header, addr, addr_len=addr_len
            )
        except RuntimeError as e:
            print(f"Could not initialize eeprom: {e}")
            eep = None
            partition = None

        # If we have block devices, try mounting the partition!
        if eep is not None and partition is not None:
            self._mount_eeprom(partition, event.port)

    async def handle_hexpansion_removal(self, event):
        print(event)

        if event.port in self.hexpansion_apps:
            self._stop_hexpansion_app(self.hexpansion_apps[event.port], event.port)

        if event.port in self.mountpoints:
            print(f"Unmounting {self.mountpoints[event.port]}")
            vfs.umount(self.mountpoints[event.port])
            del self.mountpoints[event.port]

        if self.format_dialog_port == event.port and self.format_dialog is not None:
            self.format_dialog._cleanup()
            self.format_dialog = None
            eventbus.emit(RequestForegroundPopEvent(self))

        for ls in HexpansionConfig(event.port).ls_pin:
            ls.init(ls.IN)

        for hs in HexpansionConfig(event.port).pin:
            hs.init(hs.IN)

    async def background_task(self):
        tildagonos.set_led_power(True)

        hexpansion_plugin_states = [False] * 6
        detect_pin = [
            ePin(EPIN_ND_A),
            ePin(EPIN_ND_B),
            ePin(EPIN_ND_C),
            ePin(EPIN_ND_D),
            ePin(EPIN_ND_E),
            ePin(EPIN_ND_F),
        ]
        while True:
            with PerfTimer("indicate hexpansion insertion"):
                for i, n in enumerate(
                    [EPIN_ND_A, EPIN_ND_B, EPIN_ND_C, EPIN_ND_D, EPIN_ND_E, EPIN_ND_F]
                ):
                    hexpansion_present = not detect_pin[i].value()
                    if hexpansion_present:
                        if settings.get("pattern_mirror_hexpansions", False):
                            tildagonos.leds[13 + i] = tildagonos.leds[1 + (i * 2)]
                        else:
                            tildagonos.leds[13 + i] = led_colours[i]
                    else:
                        tildagonos.leds[13 + i] = (0, 0, 0)
                    if hexpansion_present and not hexpansion_plugin_states[i]:
                        hexpansion_plugin_states[i] = True
                        eventbus.emit(HexpansionInsertionEvent(port=i + 1))
                    if not hexpansion_present and hexpansion_plugin_states[i]:
                        hexpansion_plugin_states[i] = False
                        eventbus.emit(HexpansionRemovalEvent(port=i + 1))

                tildagonos.leds.write()
            await asyncio.sleep(0.05)
