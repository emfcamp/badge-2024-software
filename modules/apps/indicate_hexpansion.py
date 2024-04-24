import asyncio
import os

from app_components.dialog import YesNoDialog
from eeprom_partition import EEPROMPartition
from perf_timer import PerfTimer
from scheduler import RequestForegroundPushEvent, RequestForegroundPopEvent, RequestStartAppEvent, RequestStopAppEvent
from tildagonos import EPIN_ND_A, EPIN_ND_B, EPIN_ND_C, EPIN_ND_D, EPIN_ND_E, EPIN_ND_F
from tildagonos import EPIN_BTN_1, EPIN_BTN_2, EPIN_BTN_3, EPIN_BTN_4, EPIN_BTN_5, EPIN_BTN_6
from tildagonos import led_colours
from eventbus import eventbus
from machine import I2C
from eeprom_i2c import EEPROM, T24C256
from events.input import ButtonDownEvent, ButtonUpEvent, Buttons
import vfs
import sys
import struct


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


class HexpansionHeader:
    _header_format = '<4s4sHHIHHH10s'
    _magic = 'THEX'

    def __init__(self,
                 manifest_version: str,
                 fs_offset: int,
                 eeprom_page_size: int,
                 eeprom_total_size: int,
                 vid: int,
                 pid: int,
                 unique_id: int,
                 friendly_name: str):
        self.manifest_version = manifest_version
        self.fs_offset = fs_offset
        self.eeprom_page_size = eeprom_page_size
        self.eeprom_total_size = eeprom_total_size
        self.vid = vid
        self.pid = pid
        self.unique_id = unique_id
        self.friendly_name = friendly_name

        self.to_bytes()

    def __str__(self):
        return f'''HexpansionHeader[
    manifest version: {self.manifest_version},
    fs offset: {self.fs_offset},
    eeprom page size: {self.eeprom_page_size},
    eeprom total size: {self.eeprom_total_size},
    vendor id: {'0x' + hex(self.vid)[2:].upper()},
    product id: {'0x' + hex(self.pid)[2:].upper()},
    unique id: {self.unique_id},
    friendly name: {self.friendly_name},
]'''

    def to_bytes(self):
        return struct.pack(
            self._header_format,
            self._magic,
            self.manifest_version,
            self.fs_offset,
            self.eeprom_page_size,
            self.eeprom_total_size,
            self.vid,
            self.pid,
            self.unique_id,
            self.friendly_name,
        )

    @classmethod
    def from_bytes(cls, buf):
        if len(buf) != 32:
            raise RuntimeError("Invalid header length, should be 32")
        if buf[0:4] != b'THEX':
            raise RuntimeError(f"Invalid magic in hexpansion header: {buf[0:4]}")
        if buf[4:8] != b'2024':
            raise RuntimeError("Unknown manifest version. Supported: [2024]")
        unpacked = struct.unpack(cls._header_format, buf)
        return cls(
            manifest_version=unpacked[1].decode().split("\x00")[0],
            fs_offset=unpacked[2],
            eeprom_page_size=unpacked[3],
            eeprom_total_size=unpacked[4],
            vid=unpacked[5],
            pid=unpacked[6],
            unique_id=unpacked[7],
            friendly_name=unpacked[8].decode().split("\x00")[0]
        )


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
            print(f"App module not found")
            self._cleanup_import_path(old_cwd, old_sys_path)
            return

        App = package.__app_export__ if hasattr(package, "__app_export__") else None

        if App is None:
            print("No exported app found")
            self._cleanup_import_path(old_cwd, old_sys_path)
            return

        print("Found app")
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
            print(f"Attempting to mount i2c eeprom from hexpansion port {port}")
            vfs.mount(eep, mountpoint)
        except Exception as e:
            print(f"Failed to mount: {e}")
            self.format_requests.append((eep, port))
            return

        self.mountpoints[port] = mountpoint
        print(f"Mounted eeprom to {mountpoint}")
        print("Hexpansion files:", os.listdir(mountpoint))

        if self.autolaunch:
            self._launch_hexpansion_app(port)

    def _read_hexpansion_header(self, i2c) -> HexpansionHeader | None:
        default_eeprom_addr = 0x50

        devices = i2c.scan()
        if default_eeprom_addr not in devices:
            print(f"No device found at {hex(default_eeprom_addr)}")
            return None

        i2c.writeto(0x50, bytes([0, 0]))
        header_bytes = i2c.readfrom(0x50, 32)

        try:
            header = HexpansionHeader.from_bytes(header_bytes)
        except RuntimeError as e:
            print(f"Failed to decode header: {e}")
            return None

        return header

    async def handle_hexpansion_insertion(self, event):
        print(event)
        # First, check the header
        i2c = I2C(event.port)
        header = self._read_hexpansion_header(i2c)
        if header is None:
            return

        print("Found hexpansion header:")
        print(header)

        try:
            eep = EEPROM(i2c=i2c,
                         chip_size=header.eeprom_total_size,
                         page_size=header.eeprom_page_size)
            partition = EEPROMPartition(eep=eep,
                                        offset=header.fs_offset,
                                        length=header.eeprom_total_size - header.fs_offset)
            print("eeprom block count:", eep.ioctl(4, None))
            print("partition block count:", partition.ioctl(4, None))
            print("partition block size:", partition.ioctl(5, None))
        except RuntimeError:
            print("Could not initialize eeprom")
            eep = None

        if eep is not None:
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
