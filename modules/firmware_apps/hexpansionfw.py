import async_helpers
import asyncio
import app
import gzip
import io
import json
import os
import requests
import settings
import vfs
from machine import I2C
from tarfile import TarFile, DIRTYPE
from app_components import layout
from app_components.dialog import HexDialog, NumberDialog, YesNoDialog, ProgressDialog
from app_components.background import Background as bg
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from system.hexpansion.events import (
    HexpansionRemovalEvent,
    HexpansionInsertionEvent,
)
from system.hexpansion.header import HexpansionHeader, write_header
from system.hexpansion.util import (
    detect_eeprom_addr,
    get_hexpansion_block_devices,
    read_hexpansion_header,
)
from system.notification.events import ShowNotificationEvent

DEFAULT_REPO = (
    "https://github.com/emfcamp/hexpansion-firmwares/releases/download/latest/"
)
_FIRMWARE_URL = "{base}/firmware_0x{vid:04x}_0x{pid:04x}.tar.gz"
_HEADER_URL = "{base}/firmware_0x{vid:04x}_0x{pid:04x}.json"
_TMP_PATH = "/firmware_dl.tar.gz"


class HexpansionDetail:
    def __init__(self, port, app, header=None):
        self.port = port
        self.app = app
        self.header = header
        self._values = {}
        self._displays = {}
        self._layout = layout.LinearLayout(items=self._build_items())
        self.dialog = None
        self.render_update = print

    def _build_items(self):
        items = []
        developer = settings.get("developer", False)
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
            if (
                self.header is None
                and field in {"vid", "pid"}
                or self.header is not None
                and field == "unique_id"
                and developer
            ):
                items.append(
                    layout.ButtonDisplay(
                        f"Enter {label}",
                        button_handler=self._make_edit_handler(field, label),
                    )
                )
        if self.header is None:
            items.append(
                layout.ButtonDisplay("Search...", button_handler=self.search_handler)
            )
        else:
            items.append(
                layout.ButtonDisplay(
                    "Update firmware", button_handler=self.update_handler
                )
            )
            if developer:
                items.append(
                    layout.ButtonDisplay(
                        "Factory reset", button_handler=self.factory_reset_handler
                    )
                )
                items.append(
                    layout.ButtonDisplay(
                        "Bulk provisioning", button_handler=self.bulk_provision_handler
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
            if field in {"vid", "pid"}:
                self.dialog = HexDialog(f"Enter {label}", self.app, on_complete=save)
            if field in {"unique_id"}:
                self.dialog = NumberDialog(f"Enter {label}", self.app, on_complete=save)
            return self.dialog

        return handler

    async def search_handler(self, _event, progress=None):
        vid = self._values.get("vid")
        pid = self._values.get("pid")
        if vid is None or pid is None:
            return True
        try:
            url = _HEADER_URL.format(
                base=settings.get("hexpansion_firmware_repo", DEFAULT_REPO),
                vid=vid,
                pid=pid,
            )
            if progress is None:
                progress = self.render_update
            response = await async_helpers.unblock(requests.get, progress, url)
            data = json.loads(response.content)
            data["vid"] = self._parse_hex(data["vid"])
            data["pid"] = self._parse_hex(data["pid"])
            self.header = HexpansionHeader(**data)
            self._displays = {}
            self._layout = layout.LinearLayout(items=self._build_items())
        except Exception:
            eventbus.emit(ShowNotificationEvent(message="No results"))
        return True

    async def update_handler(self, event):
        self.dialog = YesNoDialog(
            "Update?",
            self.app,
            on_yes=self._update_wrapper,
        )
        return True

    async def _update_wrapper(self):
        try:
            await self._update()
        except Exception:
            await eventbus.emit_async(ShowNotificationEvent(message="Update failed"))
        else:
            await eventbus.emit_async(ShowNotificationEvent(message="Updated"))
            await asyncio.sleep(0.1)
            await eventbus.emit_async(HexpansionRemovalEvent(port=self.port))
            await asyncio.sleep(0.1)
            await eventbus.emit_async(HexpansionInsertionEvent(port=self.port))
        return True

    async def _update(self):
        mountpoint = f"/hexpansion_{self.port}"
        try:
            os.stat(mountpoint)
        except OSError:
            print(f"{mountpoint} is not mounted - storing to filesystem")
            try:
                os.mkdir("/drivers")
            except OSError:
                pass
            mountpoint = f"/drivers/hex_{self.header.vid:04x}_{self.header.pid:04x}"
            try:
                os.mkdir(mountpoint)
            except OSError:
                pass

        url = _FIRMWARE_URL.format(
            base=settings.get("hexpansion_firmware_repo", DEFAULT_REPO),
            vid=self.header.vid,
            pid=self.header.pid,
        )

        await self.render_update()
        self.dialog = ProgressDialog("Downloading firmware", self.app)
        progress = self.dialog.make_progress_handler(self.render_update)

        print(f"Downloading {url}")
        response = await async_helpers.unblock(requests.get, progress, url)
        with open(_TMP_PATH, "wb") as f:
            f.write(response.content)

        if mountpoint.startswith("/drivers"):
            self.dialog.message = "Saving driver to flash"
        else:
            self.dialog.message = "Writing EEPROM"

        try:
            await progress()
            with open(_TMP_PATH, "rb") as f:
                tar_bytes = await async_helpers.unblock(
                    gzip.decompress, progress, f.read()
                )
            for entry in TarFile(fileobj=io.BytesIO(tar_bytes)):
                await progress()
                if not entry or entry.type == DIRTYPE:
                    continue
                name = entry.name.lstrip("./")
                candidates = [name]
                if name.endswith(".py"):
                    candidates.append(name[:-3] + ".mpy")
                elif name.endswith(".mpy"):
                    candidates.append(name[:-4] + ".py")
                for candidate in candidates:
                    try:
                        os.remove(f"{mountpoint}/{candidate}")
                    except OSError:
                        pass
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
                    await progress()
        finally:
            try:
                os.remove(_TMP_PATH)
                self.dialog.result = True
            except OSError:
                pass

    async def factory_reset_handler(self, event):
        self.dialog = YesNoDialog(
            "Factory reset?",
            self.app,
            on_yes=self._factory_reset_wrapper,
        )
        return True

    async def _provision_port(self, port, progress):
        i2c = I2C(port)
        await progress()
        addr, addr_len = detect_eeprom_addr(i2c)
        write_header(
            port,
            self.header,
            addr=addr,
            addr_len=addr_len,
            page_size=self.header.eeprom_page_size,
        )
        _, partition = get_hexpansion_block_devices(
            i2c, self.header, addr=addr, addr_len=addr_len
        )
        await progress()
        vfs.VfsLfs2.mkfs(partition)
        await progress()
        mountpoint = f"/hexpansion_{port}"
        try:
            vfs.umount(mountpoint)
        except OSError:
            pass
        vfs.mount(partition, mountpoint)

        with open(_TMP_PATH, "rb") as f:
            tar_bytes = await async_helpers.unblock(gzip.decompress, progress, f.read())
        tar = TarFile(fileobj=io.BytesIO(tar_bytes))
        for entry in tar:
            await progress()
            if not entry or entry.type == DIRTYPE:
                continue
            name = entry.name.lstrip("./")
            print(f"Extracting {name}")
            archive_file = tar.extractfile(entry)
            if archive_file is None:
                continue
            with open(f"{mountpoint}/{name}", "wb") as f:
                f.write(archive_file.read())
                await progress()

    async def _factory_reset_wrapper(self):
        try:
            await self._factory_reset()
        except Exception:
            await eventbus.emit_async(ShowNotificationEvent(message="Reset failed"))
        else:
            await eventbus.emit_async(ShowNotificationEvent(message="Factory reset"))
            await asyncio.sleep(0.1)
            await eventbus.emit_async(HexpansionRemovalEvent(port=self.port))
            await asyncio.sleep(0.1)
            await eventbus.emit_async(HexpansionInsertionEvent(port=self.port))
        return True

    async def _factory_reset(self):
        url = _FIRMWARE_URL.format(
            base=settings.get("hexpansion_firmware_repo", DEFAULT_REPO),
            vid=self.header.vid,
            pid=self.header.pid,
        )

        await self.render_update()

        self.dialog = ProgressDialog("Loading metadata", self.app)
        uid = self._values.get("unique_id", 0)
        progress = self.dialog.make_progress_handler(self.render_update)
        await self.search_handler(None, progress)
        self._values["unique_id"] = uid

        self.dialog.message = "Downloading firmware"
        response = await async_helpers.unblock(requests.get, progress, url)
        with open(_TMP_PATH, "wb") as f:
            f.write(response.content)
        self.dialog.message = "Writing EEPROM"
        try:
            await self._provision_port(self.port, progress)
        finally:
            try:
                os.remove(_TMP_PATH)
            except OSError:
                pass
            self.dialog.result = True

    async def bulk_provision_handler(self, _event):
        await self._bulk_provision()
        return True

    async def _bulk_provision(self):
        url = _FIRMWARE_URL.format(
            base=settings.get("hexpansion_firmware_repo", DEFAULT_REPO),
            vid=self.header.vid,
            pid=self.header.pid,
        )
        print(f"Downloading {url}")
        response = await async_helpers.unblock(requests.get, self.render_update, url)
        with open(_TMP_PATH, "wb") as f:
            f.write(response.content)

        eventbus.emit(ShowNotificationEvent(message="Bulk mode enabled"))
        eventbus.on_async(HexpansionInsertionEvent, self.bulk_insert, self.app)

    def _cleanup(self):
        eventbus.remove(HexpansionInsertionEvent, self.bulk_insert, self.app)

    async def bulk_insert(self, event):
        self.header.unique_id += 1
        print(f"Provisioning port {event.port} with unique_id {self.header.unique_id}")
        try:
            await self._provision_port(event.port, self.render_update)
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
        self.render_update = render_update
        while True:
            if self.dialog:
                dialog = self.dialog
                await self.dialog.run(render_update)
                if self.dialog == dialog:
                    self.dialog = None
            await render_update()


class HexpansionInfoApp(app.App):
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self._layout = layout.LinearLayout(items=self._build_items())
        eventbus.on_async(ButtonDownEvent, self._button_handler, self)
        eventbus.on(HexpansionInsertionEvent, self._rebuild_items, self)
        eventbus.on(HexpansionRemovalEvent, self._rebuild_items, self)
        self.submenu = None

    def _rebuild_items(self, event=None):
        self._layout.items = self._build_items()
        self._layout.y_offset = 120

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
