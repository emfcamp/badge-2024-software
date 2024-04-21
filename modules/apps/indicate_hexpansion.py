import asyncio

from app_components.dialog import YesNoDialog
from perf_timer import PerfTimer
from scheduler import RequestForegroundPushEvent, RequestForegroundPopEvent
from tildagonos import EPIN_ND_A, EPIN_ND_B, EPIN_ND_C, EPIN_ND_D, EPIN_ND_E, EPIN_ND_F
from tildagonos import EPIN_BTN_1, EPIN_BTN_2, EPIN_BTN_3, EPIN_BTN_4, EPIN_BTN_5, EPIN_BTN_6
from tildagonos import led_colours
from eventbus import eventbus
from machine import I2C
from eeprom_i2c import EEPROM, T24C256
from events.input import ButtonDownEvent, ButtonUpEvent, Buttons
import vfs
import sys

class HexpansionInsertionEvent:
    def __init__(self, port):
        self.port = port

    def __str__(self):
        return f"Hexpansion inserted in port: {self.port}"


class HexpansionRemovalEvent:
    def __init__(self, port):
        self.port = port

    def __str__(self):
        return f"Hexpansion removed from port: {self.port}"


class HexpansionFormattedEvent:
    def __init__(self, port):
        self.port = port

class HexpansionMountedEvent:
    def __init__(self, port):
        self.port = port

class HexpansionInsertionApp:
    def __init__(self, tildagonos, autolaunch=True):
        self.tildagonos = tildagonos
        eventbus.on_async(HexpansionInsertionEvent, self.handle_hexpansion_insertion, self)
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
                app=self
            )

            self.format_dialog_port = port

            eventbus.emit(RequestForegroundPushEvent(self))

    def draw(self, ctx):
        if self.format_dialog is not None:
            self.format_dialog.draw(ctx)

    def _launch_hexpansion_app(self, port):
        if port not in self.mountpoints:
            return

        mount = self.mountpoints[port]

        old_sys_path = sys.path[:]

        sys.path.clear()
        sys.path.append(mount)

        try:
            package = __import__("app")
            print("Found app package")
        except ImportError as e:
            print(e)
            print(f"App module not found")
            sys.path.clear()
            for p in old_sys_path:
                sys.path.append(p)
            return

        App = package.__app_export__ if hasattr(package, "__app_export__") else None

        if App is None:
            print("No exported app found")
            sys.path.clear()
            for p in old_sys_path:
                sys.path.append(p)
            return

        print("Found app")

        from scheduler import scheduler
        scheduler.start_app(App())

        sys.path.clear()
        for p in old_sys_path:
            sys.path.append(p)


    def _format_eeprom(self, eep):
        print("Formatting...")
        vfs.VfsLfs2.mkfs(eep)

    def _mount_eeprom(self, eep, port):
        mountpoint = f"/hexpansion_{port}"

        try:
            print(f"Attempting to mount i2c eeprom from hexpansion port {port}")
            vfs.mount(eep, mountpoint)
        except Exception as e:
            print(f"Failed to mount: {e}")
            self.format_requests.append((eep, port))
            return

        self.mountpoints[port] = mountpoint
        print(f"Mounted eeprom to {mountpoint}")
        if self.autolaunch:
            self._launch_hexpansion_app(port)

    async def handle_hexpansion_insertion(self, event):
        print(event)

        try:
            # TODO: Automatically determine eeprom size
            eep = EEPROM(I2C(event.port), T24C256)
        except RuntimeError:
            print("No eeprom found")
            eep = None

        if eep is not None:
            self._mount_eeprom(eep, event.port)

    async def handle_hexpansion_removal(self, event):
        print(event)
        if event.port in self.mountpoints:
            print(f"Unmounting {self.mountpoints[event.port]}")
            vfs.umount(self.mountpoints[event.port])
            del self.mountpoints[event.port]

        if self.format_dialog_port == event.port and self.format_dialog is not None:
            self.format_dialog._cleanup()
            self.format_dialog = None
            eventbus.emit(RequestForegroundPopEvent(self))

    async def background_update(self):
        self.tildagonos.set_led_power(True)

        hexpansion_plugin_states = [False] * 6
        button_states = [False] * 6

        while True:
            with PerfTimer("indicate hexpansion insertion"):
                self.tildagonos.read_egpios()
                self.tildagonos.leds.fill((0, 0, 0))

                for i, n in enumerate([EPIN_ND_A, EPIN_ND_B, EPIN_ND_C, EPIN_ND_D, EPIN_ND_E, EPIN_ND_F]):
                    hexpansion_present = not self.tildagonos.check_egpio_state(n, readgpios=False)
                    if hexpansion_present:
                        self.tildagonos.leds[13 + i] = led_colours[i]
                    if hexpansion_present and not hexpansion_plugin_states[i]:
                        hexpansion_plugin_states[i] = True
                        eventbus.emit(HexpansionInsertionEvent(port=i + 1))
                    if not hexpansion_present and hexpansion_plugin_states[i]:
                        hexpansion_plugin_states[i] = False
                        eventbus.emit(HexpansionRemovalEvent(port=i + 1))

                for i, n in enumerate([EPIN_BTN_1, EPIN_BTN_2, EPIN_BTN_3, EPIN_BTN_4, EPIN_BTN_5, EPIN_BTN_6]):
                    button_down = not self.tildagonos.check_egpio_state(n, readgpios=False)
                    if button_down:
                        if i:
                            self.tildagonos.leds[i * 2] = led_colours[i]
                        else:
                            self.tildagonos.leds[12] = led_colours[i]
                        self.tildagonos.leds[1 + i * 2] = led_colours[i]
                    if button_down and not button_states[i]:
                        button_states[i] = True
                        eventbus.emit(ButtonDownEvent(button=i))
                    if not button_down and button_states[i]:
                        button_states[i] = False
                        eventbus.emit(ButtonUpEvent(button=i))

                self.tildagonos.leds.write()
            await asyncio.sleep(0)
