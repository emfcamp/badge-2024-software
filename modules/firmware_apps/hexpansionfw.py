import app
import gzip
import io
import json
import os
import requests
import vfs
from machine import I2C
from tarfile import TarFile, DIRTYPE
from app_components import layout
from app_components.dialog import HexDialog, YesNoDialog
from app_components.background import Background as bg
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from system.hexpansion.events import HexpansionInsertionEvent
from system.hexpansion.header import HexpansionHeader, write_header
from system.hexpansion.util import (
    detect_eeprom_addr,
    get_hexpansion_block_devices,
    read_hexpansion_header,
)
from system.notification.events import ShowNotificationEvent

_FIRMWARE_URL = "https://github.com/MatthewWilkes/hexpansion-firmwares/releases/download/latest/firmware_0x{vid:04X}_0x{pid:04X}.tar.gz"
_HEADER_URL = "https://github.com/MatthewWilkes/hexpansion-firmwares/releases/download/latest/firmware_0x{vid:04X}_0x{pid:04X}.json"
_TMP_PATH = "/firmware_dl.tar.gz"


def compare_firmware(vid, pid, port):
    url = _FIRMWARE_URL.format(vid=vid, pid=pid)
    mountpoint = f"/hexpansion_{port}"

    print(f"Downloading {url}")
    response = requests.get(url)
    with open(_TMP_PATH, "wb") as f:
        f.write(response.content)

    try:
        with open(_TMP_PATH, "rb") as f:
            tar_bytes = gzip.decompress(f.read())

        tar = TarFile(fileobj=io.BytesIO(tar_bytes))
        for entry in tar:
            if not entry or entry.type == DIRTYPE:
                continue
            name = entry.name.lstrip("./")
            device_path = f"{mountpoint}/{name}"
            print(f"Comparing {name}")
            archive_file = tar.extractfile(entry)
            if archive_file is None:
                continue
            archive_data = archive_file.read()
            try:
                with open(device_path, "rb") as f:
                    device_data = f.read()
                if device_data == archive_data:
                    print("  match")
                else:
                    print(
                        f"  mismatch (device {len(device_data)}B, archive {len(archive_data)}B)"
                    )
            except OSError:
                print("  not found on device")
    finally:
        try:
            os.remove(_TMP_PATH)
        except OSError:
            pass


class HexpansionDetail:
    def __init__(self, port, app, header=None):
        self.port = port
        self.app = app
        self.header = header
        self._values = {}
        self._displays = {}
        self._layout = layout.LinearLayout(items=self._build_items())
        self.dialog = None

    def _build_items(self):
        items = []
        for field, label, parse, fmt, empty, show_without_header in [
            ("friendly_name", "Name", str, str, "Unknown", False),
            ("vid", "VID", self._parse_hex, lambda v: f"0x{v:04X}", "N/A", True),
            ("pid", "PID", self._parse_hex, lambda v: f"0x{v:04X}", "N/A", True),
            ("unique_id", "Unique ID", int, lambda v: f"{v}", "N/A", False),
        ]:
            value = fmt(getattr(self.header, field)) if self.header else empty
            display = layout.DefinitionDisplay(label, value)
            self._displays[field] = (display, parse, fmt)
            items.append(display)
            if self.header is None and show_without_header:
                items.append(
                    layout.ButtonDisplay(
                        "Enter", button_handler=self._make_edit_handler(field, label)
                    )
                )
        if self.header is None:
            items.append(
                layout.ButtonDisplay("Search...", button_handler=self.search_handler)
            )
        else:
            items.append(
                layout.ButtonDisplay("Update", button_handler=self.update_handler)
            )
            items.append(
                layout.ButtonDisplay(
                    "Bulk provision", button_handler=self.bulk_provision_handler
                )
            )
            items.append(
                layout.ButtonDisplay(
                    "Factory reset", button_handler=self.factory_reset_handler
                )
            )
        return items

    @staticmethod
    def _parse_hex(s):
        s = s.strip()
        if s.lower().startswith("0x"):
            s = s[2:]
        return int(s, 16)

    def _make_edit_handler(self, field, label):
        display, parse, fmt = self._displays[field]

        def save():
            try:
                value = parse(self.dialog.text)
                self._values[field] = value
                if self.header is not None:
                    setattr(self.header, field, value)
                display.value = fmt(value)
            except ValueError:
                pass

        async def handler(_event):
            self.dialog = HexDialog(f"Enter {label}", self.app, on_complete=save)
            return self.dialog

        return handler

    async def search_handler(self, _event):
        vid = self._values.get("vid")
        pid = self._values.get("pid")
        if vid is None or pid is None:
            return True
        try:
            url = _HEADER_URL.format(vid=vid, pid=pid)
            response = requests.get(url)
            data = json.loads(response.content)
            data["vid"] = self._parse_hex(data["vid"])
            data["pid"] = self._parse_hex(data["pid"])
            self.header = HexpansionHeader(**data)
            self._displays = {}
            self._layout = layout.LinearLayout(items=self._build_items())
        except Exception:
            eventbus.emit(ShowNotificationEvent(message="No results"))
        return True

    async def update_handler(self, _event):
        try:
            await self._update()
        except Exception:
            eventbus.emit(ShowNotificationEvent(message="Update failed"))
        else:
            eventbus.emit(ShowNotificationEvent(message="Updated"))
        return True

    async def _update(self):
        mountpoint = f"/hexpansion_{self.port}"
        try:
            os.stat(mountpoint)
        except OSError:
            print(f"{mountpoint} is not mounted")
            return

        url = _FIRMWARE_URL.format(vid=self.header.vid, pid=self.header.pid)
        print(f"Downloading {url}")
        response = requests.get(url)
        with open(_TMP_PATH, "wb") as f:
            f.write(response.content)

        try:
            with open(_TMP_PATH, "rb") as f:
                tar_bytes = gzip.decompress(f.read())
            tar = TarFile(fileobj=io.BytesIO(tar_bytes))
            for entry in tar:
                if not entry or entry.type == DIRTYPE:
                    continue
                name = entry.name.lstrip("./")
                print(f"Extracting {name}")
                archive_file = tar.extractfile(entry)
                if archive_file is None:
                    continue
                with open(f"{mountpoint}/{name}", "wb") as f:
                    f.write(archive_file.read())
        finally:
            try:
                os.remove(_TMP_PATH)
            except OSError:
                pass

    async def factory_reset_handler(self, event):
        self.dialog = YesNoDialog(
            "Factory reset?", self.app, on_yes=self._factory_reset
        )
        return True

    def _provision_port(self, port):
        i2c = I2C(port)
        addr, addr_len = detect_eeprom_addr(i2c)
        write_header(port, self.header, addr=addr, addr_len=addr_len)
        _, partition = get_hexpansion_block_devices(
            i2c, self.header, addr=addr, addr_len=addr_len
        )
        vfs.VfsLfs2.mkfs(partition)
        mountpoint = f"/hexpansion_{port}"
        try:
            vfs.umount(mountpoint)
        except OSError:
            pass
        vfs.mount(partition, mountpoint)

        with open(_TMP_PATH, "rb") as f:
            tar_bytes = gzip.decompress(f.read())
        tar = TarFile(fileobj=io.BytesIO(tar_bytes))
        for entry in tar:
            if not entry or entry.type == DIRTYPE:
                continue
            name = entry.name.lstrip("./")
            print(f"Extracting {name}")
            archive_file = tar.extractfile(entry)
            if archive_file is None:
                continue
            with open(f"{mountpoint}/{name}", "wb") as f:
                f.write(archive_file.read())

    def _factory_reset(self):
        url = _FIRMWARE_URL.format(vid=self.header.vid, pid=self.header.pid)
        print(f"Downloading {url}")
        response = requests.get(url)
        with open(_TMP_PATH, "wb") as f:
            f.write(response.content)
        try:
            self._provision_port(self.port)
        except Exception:
            eventbus.emit(ShowNotificationEvent(message="Failed to reset"))
        finally:
            try:
                os.remove(_TMP_PATH)
            except OSError:
                pass
            eventbus.emit(ShowNotificationEvent(message="Reset complete"))

    async def bulk_provision_handler(self, _event):
        await self._bulk_provision()
        return True

    async def _bulk_provision(self):
        url = _FIRMWARE_URL.format(vid=self.header.vid, pid=self.header.pid)
        print(f"Downloading {url}")
        response = requests.get(url)
        with open(_TMP_PATH, "wb") as f:
            f.write(response.content)

        eventbus.emit(ShowNotificationEvent(message="Bulk mode enabled"))
        eventbus.on(HexpansionInsertionEvent, self.bulk_insert, self.app)

    def _cleanup(self):
        eventbus.remove(HexpansionInsertionEvent, self.bulk_insert, self.app)

    def bulk_insert(self, event):
        self.header.unique_id += 1
        print(f"Provisioning port {event.port} with unique_id {self.header.unique_id}")
        try:
            self._provision_port(event.port)
        except Exception:
            eventbus.emit(ShowNotificationEvent(message="Failed to provision"))
        else:
            eventbus.emit(
                ShowNotificationEvent(message=f"Provisioned {self.header.unique_id}")
            )
        self._layout = layout.LinearLayout(items=self._build_items())

    async def button_event(self, event):
        if not self.dialog:
            return await self._layout.button_event(event)

    def draw(self, ctx):
        bg.draw(ctx)
        self._layout.draw(ctx)

    async def run(self, render_update):
        while True:
            if self.dialog:
                await self.dialog.run(render_update)
                self.dialog = None
            await render_update()


class HexpansionInfoApp(app.App):
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self._layout = layout.LinearLayout(items=self._build_items())
        eventbus.on_async(ButtonDownEvent, self._button_handler, self)
        self.submenu = None

    def _build_items(self):
        items = []
        for port in range(7):
            vid, pid = None, None
            header = None
            allow_provisioning = False
            try:
                i2c = I2C(port)
                addr, addr_len = detect_eeprom_addr(i2c)
                if addr is None:
                    value = "None"
                else:
                    header = read_hexpansion_header(i2c, addr, addr_len=addr_len)
                    allow_provisioning = True
                    if header is None:
                        value = "Unprovisioned"
                    else:
                        value = header.friendly_name
            except Exception as e:
                value = f"error: {e}"

            def make_handler(port, vid, pid, header):
                async def handler(event):
                    if BUTTON_TYPES["CONFIRM"] in event.button:
                        self.submenu = HexpansionDetail(port, self, header)
                        return True
                    return False

                return handler

            items.append(
                layout.DefinitionDisplay(
                    f"Port {port}" if port else "Frontboard", value
                )
            )
            if allow_provisioning:
                items.append(
                    layout.ButtonDisplay(
                        "Configure...",
                        button_handler=make_handler(port, vid, pid, header),
                    )
                )
        return items

    async def _button_handler(self, event):
        if not self.overlays:
            if self.submenu:
                handled = await self.submenu.button_event(event)
                if not handled and BUTTON_TYPES["CANCEL"] in event.button:
                    self.submenu._cleanup()
                    self.submenu = None
            else:
                handled = await self._layout.button_event(event)
                if not handled and BUTTON_TYPES["CANCEL"] in event.button:
                    self.minimise()

    def draw(self, ctx):
        bg.draw(ctx)

        if self.submenu:
            self.submenu.draw(ctx)
        else:
            self._layout.draw(ctx)

        self.draw_overlays(ctx)

    async def run(self, render_update):
        while True:
            if self.submenu:
                await self.submenu.run(render_update)
            await render_update()


__app_export__ = HexpansionInfoApp
