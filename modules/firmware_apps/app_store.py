import gc
import gzip
import io
import json
import os
import tarfile
import time
from tarfile import DIRTYPE, TarFile
from typing import Any, Callable
from perf_timer import PerfTimer
from math import radians, pi
import app
import async_helpers
import wifi
import shutil
import machine
from app_components import Menu, fourteen_pt, sixteen_pt, twelve_pt, ten_pt, seven_pt
from app_components.dialog import TextDialog
from app_components.tokens import set_color
from app_components.utils import wrap_text
from events.input import BUTTON_TYPES, ButtonDownEvent
from events.emote import EmoteNegativeEvent, EmotePositiveEvent
from frontboards.common import FRONTBOARD_BUTTON_TYPES
from requests import get
from system.eventbus import eventbus
from system.launcher.events import (
    InstallNotificationEvent,
)
from system.launcher.utils import (
    APP_DIR,
    APP_INSTALL_DIR,
    load_info,
    load_manifest,
)
from system.notification.events import ShowNotificationEvent
from app_components.background import Background as bg
from firmware_apps.settings_app import BG_DIR, PAT_DIR
from random import random, choice, randint
from app_components.tokens import symbols

import hashlib


def get_first_category(manifest):
    """Extract the first category from an app manifest.

    Categories can be a string or a list of strings. This always returns a
    single string (the first element if it's a list).
    """
    category = manifest.get("category")
    if isinstance(category, list):
        return category[0] if category else None
    return category


def dir_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) != 0
    except OSError:
        return False


APP_STORE_API_BASE = "https://apps.badge.emfcamp.org/v1"


def _quote(s):
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    res = []
    for c in str(s):
        if c in safe:
            res.append(c)
        else:
            for b in c.encode("utf-8"):
                res.append("%%%02X" % b)
    return "".join(res)


def _build_app_url(path, params=None):
    """Build an app store API URL with optional query parameters."""
    url = f"{APP_STORE_API_BASE}{path}"
    if params:
        parts = []
        for key, values in params.items():
            if isinstance(values, (list, tuple)):
                for v in values:
                    parts.append(f"{_quote(key)}={_quote(v)}")
            else:
                parts.append(f"{_quote(key)}={_quote(values)}")
        if parts:
            url = f"{url}?{'&'.join(parts)}"
    return url


def compute_app_code(service, owner, title):
    payload = service + owner + title
    h = hashlib.md5(payload.encode())
    digest = h.digest()
    code = "".join(chr(ord("0") + (b % 5)) for b in digest[:8])
    return code


def _get_app_code_from_metadata(app_dir, folder_name):
    info = load_info(app_dir, folder_name)
    return info.get("app_code")


def _find_app_codes(app_dir, folder_name, manifest):
    stored = _get_app_code_from_metadata(app_dir, folder_name)
    if stored:
        return [stored]

    manifest_app = manifest.get("app", {})
    manifest_name = manifest_app.get("name", "")
    manifest_author = manifest.get("metadata", {}).get("author", "")

    candidates = []
    parts = folder_name.split("_")

    if manifest_author:
        candidates.append((manifest_author, folder_name))
        if manifest_name and manifest_name != folder_name:
            candidates.append((manifest_author, manifest_name))
        if len(parts) >= 2:
            candidates.append((manifest_author, parts[-1]))

    if len(parts) >= 2:
        for split_idx in range(1, len(parts)):
            owner_us = "_".join(parts[:split_idx])
            title_us = "_".join(parts[split_idx:])
            candidates.append((owner_us, title_us))
            # Also try hyphenated variants: install_app replaces hyphens
            # with underscores, so the folder loses the original separators.
            title_hy = "-".join(parts[split_idx:])
            if title_hy != title_us:
                candidates.append((owner_us, title_hy))
            owner_hy = "-".join(parts[:split_idx])
            if owner_hy != owner_us:
                candidates.append((owner_hy, title_us))
            if owner_hy != owner_us and title_hy != title_us:
                candidates.append((owner_hy, title_hy))
    else:
        candidates.append(("emfcamp", folder_name))
        candidates.append(("badge", folder_name))

    codes = []
    seen = set()
    for service in APP_STORE_SERVICES:
        for owner, title in candidates:
            code = compute_app_code(service, owner, title)
            if code and code not in seen:
                seen.add(code)
                codes.append(code)

    return codes


def _store_app_code(app_dir, folder_name, code):
    metadata_path = f"{app_dir}/{folder_name}/metadata.json"
    try:
        with open(metadata_path, "r") as f:
            metadata = json.loads(f.read())
    except Exception:
        return
    if metadata.get("app_code") != code:
        metadata["app_code"] = code
        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)
        except Exception as e:
            print(f"[AppStore] Failed to store app code: {e}")


def _get_available_capabilities():
    caps = {}

    try:
        from frontboards.utils import detect_frontboard

        fb = detect_frontboard()
        if (fb & 0xFF00) == 0x2600:
            caps["frontboard"] = "2026 Frontboard"
        elif (fb & 0xFF00) == 0x2400:
            caps["frontboard"] = "2024 Frontboard"
    except Exception:
        pass

    try:
        from system.hexpansion.app import _hexpansion_manager

        for port, header in _hexpansion_manager.hexpansion_headers.items():
            if header is not None:
                caps.setdefault("hexpansions", []).append(
                    {"vid": hex(header.vid), "pid": hex(header.pid)}
                )
    except Exception:
        pass

    try:
        from system.capabilities.utils import list_capabilities

        for entry in list_capabilities():
            for cap in entry.get("capabilities", []):
                caps.setdefault("capabilities", []).append(cap)
    except Exception:
        pass

    return caps


CODE_INSTALL = "Use Code"
SEARCH = "Search"
AVAILABLE = "Browse Apps"
CAPABILITIES = "By Capability"
INSTALLED = "Uninstall"
UPDATE = "Update Apps"

# TODO: These categories are coupled to the server-side category list.
# If categories change on the server, this list must be updated.
APP_STORE_CATEGORIES = [
    "Badge",
    "Music",
    "Media",
    "Apps",
    "Games",
    "Background",
    "Pattern",
]

APP_STORE_SERVICES = ["github", "codeberg"]


def list_apps(dir, callable):
    with PerfTimer("List user apps"):
        apps = []
        try:
            contents = os.listdir(dir)
        except OSError:
            try:
                os.mkdir(dir)
            except OSError:
                pass
            return []

        for name in contents:
            app = {
                "path": f"{dir[1:]}.{name}.app",
                "callable": callable,
                "name": name,
                "folder": name,
                "hidden": False,
            }
            metadata = load_info(dir, name)
            if "version" not in metadata:
                app["version"] = "0.0.0"
            app.update(metadata)
            apps.append(app)
        return apps


def list_all_apps():
    app_list = []
    for d in APP_DIR:
        app_list.extend(list_apps(d, "__app_export__"))
    app_list += list_apps(BG_DIR, "__Background__")
    app_list += list_apps(PAT_DIR, "__Pattern_Export__")
    return app_list


class AppStoreApp(app.App):
    state = "init"

    def __init__(self):
        super().__init__()
        self.menu = None
        self.available_categories_menu = None
        self.available_menu = None
        self.installed_menu = None
        self.update_menu = None
        self.capabilities_menu = None
        self.capability_apps_menu = None
        self.codeinstall = None
        self.app_details = None
        self.details_app = None
        self.available_menu_position = 0
        self.response = None
        self._filtered_apps = []
        self.app_categories = APP_STORE_CATEGORIES
        self.category_filter = None
        self.available_capabilities = None
        self.category_apps_response = None
        self.capability_apps_response = None
        self.to_install_app = None
        self._lookup_code = None
        self._capability_params = None
        self._last_error = None
        self._search_query = None
        self._search_results = None
        self.search_results_menu = None
        self._app_details_return_state = None
        self._update_code_map = {}
        self._update_results = {}
        self._update_all_list = []
        self._update_install_queue = []
        self._update_all_in_progress = False
        self._update_detail_app = None
        self._update_detail_widget = None
        self._update_phase = 0
        self._update_unmatched = []
        self._update_updatable = False
        self._update_installed_apps = None
        self._capability_entries = []
        self.overlays = []

        eventbus.on(ButtonDownEvent, self._handle_error_back, self)

    def _handle_error_back(self, event: ButtonDownEvent):
        if self.state in (
            "no_wifi",
            "no_index",
            "install_oom",
        ):
            if FRONTBOARD_BUTTON_TYPES["F"] in event.button:
                self._last_error = None
                self.update_state("main_menu")

    def cleanup_ui_widgets(self):
        widgets = [
            self.menu,
            self.available_categories_menu,
            self.available_menu,
            self.installed_menu,
            self.update_menu,
            self.capabilities_menu,
            self.capability_apps_menu,
            self.codeinstall,
            self.app_details,
            self._update_detail_widget,
            self.search_results_menu,
        ]

        for widget in widgets:
            if widget:
                widget._cleanup()

            self.menu = None
            self.available_categories_menu = None
            self.available_menu = None
            self.installed_menu = None
            self.update_menu = None
            self.capabilities_menu = None
            self.capability_apps_menu = None
            self.codeinstall = None
            self.app_details = None
            self._update_detail_widget = None
            self.search_results_menu = None

    def _start_update_check(self):
        if not wifi.status():
            self.update_state("no_wifi")
            return
        installed_apps = list_all_apps()
        if not installed_apps:
            self.update_state("main_menu")
            eventbus.emit(ShowNotificationEvent("No apps installed"))
            return
        self._update_installed_apps = installed_apps

        self._update_code_map = {}
        for ia in installed_apps:
            folder = ia.get("folder", "")
            app_dir = ia.get("app_dir", APP_INSTALL_DIR)
            manifest = load_manifest(app_dir, folder)
            if not manifest:
                for d in [BG_DIR, PAT_DIR] + APP_DIR:
                    manifest = load_manifest(d, folder)
                    if manifest:
                        app_dir = d
                        break
            codes = _find_app_codes(app_dir, folder, manifest)
            if codes:
                ia["app_dir"] = app_dir
                for code in codes:
                    self._update_code_map.setdefault(code, []).append(ia)
            else:
                print(f"[AppStore] Could not compute any codes for {folder}")

        if not self._update_code_map:
            self.update_state("main_menu")
            eventbus.emit(ShowNotificationEvent("No update codes available"))
            return

        self._update_results = {}
        self._update_phase = 0
        self._update_unmatched = []
        self.update_state("checking_updates")

    def _install_next_from_queue(self):
        """Install the next app in the update queue, if any."""
        if self._update_install_queue:
            self.to_install_app = self._update_install_queue.pop(0)
            self.update_state("installing_app")

    def get_category_apps(self, category):
        """Fetch apps filtered by category from the API."""
        if not wifi.status():
            self.update_state("no_wifi")
            return
        self.category_filter = category
        self.update_state("refreshing_category_apps")

    def get_capability_apps(self, params):
        """Fetch apps filtered by capability params from the API.

        Args:
            params: Dict of query parameters to pass to the API.
        """
        if not wifi.status():
            self.update_state("no_wifi")
            return
        self._capability_params = params
        self.update_state("refreshing_capability_apps")

    def handle_category_apps(self):
        """Process category-filtered API response."""
        if not self.category_apps_response:
            print("No category apps response")
            self.update_state("available_categories_menu")
            return

        status = getattr(self.category_apps_response, "status_code", 0)
        if status != 200:
            print(f"Category apps returned status {status}")
            self.update_state("no_index")
            self._last_error = f"HTTP {status}"
            return

        try:
            self._filtered_apps = self.category_apps_response.json()["items"]
        except Exception:
            print(self.category_apps_response)
            self.update_state("available_categories_menu")
            return

        if not self._filtered_apps:
            eventbus.emit(
                ShowNotificationEvent(f"No apps found in {self.category_filter}")
            )
            self.update_state("available_categories_menu")
            return

        self.update_state("available_menu")

    def handle_capability_apps(self):
        """Process capability-filtered API response."""
        if not self.capability_apps_response:
            print("No capability apps response")
            self.update_state("capabilities_menu")
            return

        status = getattr(self.capability_apps_response, "status_code", 0)
        if status != 200:
            print(f"Capability apps returned status {status}")
            self.update_state("no_index")
            self._last_error = f"HTTP {status}"
            return

        try:
            self._filtered_apps = self.capability_apps_response.json()["items"]
        except Exception:
            print(self.capability_apps_response)
            self.update_state("capabilities_menu")
            return

        if not self._filtered_apps:
            eventbus.emit(ShowNotificationEvent("No apps found for this capability"))
            self.update_state("capabilities_menu")
            return

        self.update_state("capability_apps_menu")

    def install_app(self, app):
        """Install a single app. Returns True on success, False on failure.

        On failure this sets the appropriate error state and notifies the
        user; on success the caller is responsible for state transitions
        and notifications (single install vs "Update All" differ).
        """
        try:
            install_app(app)
        except MemoryError:
            self.update_state("install_oom")
            return False
        except Exception as e:
            print(e)
            eventbus.emit(ShowNotificationEvent("Couldn't install app"))
            eventbus.emit(EmoteNegativeEvent())
            self.update_state("main_menu")
            return False
        return True

    def update_state(self, state):
        print(f"State Transition: '{self.state}' -> '{state}'")
        self.state = state

    def handle_code_input(self, code):
        print(f"Looking up app by code: {code}")
        if not wifi.status():
            self.update_state("no_wifi")
            return
        self._lookup_code = code
        self.update_state("looking_up_code")

    def handle_code_lookup_response(self):
        """Process the response from looking up an app by code."""
        code = self._lookup_code
        if not self.response:
            print(f"No response for code lookup: {code}")
            eventbus.emit(ShowNotificationEvent(f"App {code} not found"))
            self.update_state("main_menu")
            return

        status = getattr(self.response, "status_code", 0)
        if status == 404:
            print(f"App {code} not found (404)")
            eventbus.emit(ShowNotificationEvent(f"App {code} not found"))
            self.update_state("main_menu")
            return
        elif status != 200:
            print(f"App lookup failed with status {status}")
            eventbus.emit(ShowNotificationEvent(f"Server error ({status})"))
            self.update_state("main_menu")
            return

        try:
            app = self.response.json()
            self.to_install_app = app
            self.update_state("installing_app")
        except Exception:
            print(f"Failed to parse response for code {code}")
            eventbus.emit(ShowNotificationEvent(f"App {code} not found"))
            self.update_state("main_menu")

    def prepare_available_categories_menu(self):
        def on_select(_, i):
            self.cleanup_ui_widgets()
            self.get_category_apps(self.app_categories[i])

        def exit_available_categories_menu():
            self.cleanup_ui_widgets()
            self.update_state("main_menu")

        self.available_categories_menu = Menu(
            self,
            menu_items=self.app_categories,
            select_handler=on_select,
            back_handler=exit_available_categories_menu,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def prepare_capabilities_menu(self):
        self.update_state("loading_capabilities")

    def _build_capabilities_menu(self):
        caps = self.available_capabilities
        self._capability_entries = []

        fb = caps.get("frontboard")
        if fb:
            short = fb.replace(" Frontboard", "")
            self._capability_entries.append(
                (f"FB: {short}", f"Frontboard: {fb}", {"frontboard": fb})
            )

        for h in caps.get("hexpansions", []):
            short = f"{h['vid']}:{h['pid']}"
            self._capability_entries.append(
                (
                    f"HX: {short}",
                    f"Hexpansion {short}",
                    {"vid": h["vid"], "pid": h["pid"]},
                )
            )

        seen_caps = set()
        for c in caps.get("capabilities", []):
            if c in seen_caps:
                continue
            seen_caps.add(c)
            short = c.rstrip("/").rsplit("/", 1)[-1]
            self._capability_entries.append(
                (short, f"Capability: {c}", {"capability": [c]})
            )

        if not self._capability_entries:
            eventbus.emit(ShowNotificationEvent("No capabilities detected"))
            self.update_state("main_menu")
            return

        def on_select(_, i):
            self.cleanup_ui_widgets()
            self.get_capability_apps(self._capability_entries[i][2])

        def exit_capabilities_menu():
            self.cleanup_ui_widgets()
            self.update_state("main_menu")

        self.capabilities_menu = Menu(
            self,
            menu_items=[entry[0] for entry in self._capability_entries],
            info_items=[entry[1] for entry in self._capability_entries],
            select_handler=on_select,
            back_handler=exit_capabilities_menu,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def prepare_capability_apps_menu(self):
        """Build menu of apps matching the selected capability."""

        def on_select(_, i):
            self.to_install_app = self._filtered_apps[i]
            self.update_state("installing_app")
            self.cleanup_ui_widgets()

        def exit_capability_apps_menu():
            self.cleanup_ui_widgets()
            self.update_state("capabilities_menu")

        self.capability_apps_menu = Menu(
            self,
            menu_items=[app["manifest"]["app"]["name"] for app in self._filtered_apps],
            info_items=[
                app["manifest"]["metadata"]["description"]
                for app in self._filtered_apps
            ],
            select_handler=on_select,
            back_handler=exit_capability_apps_menu,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def prepare_available_menu(self):
        def on_select(_, i):
            self.details_app = self._filtered_apps[i]
            self.available_menu_position = i
            self._app_details_return_state = "available_menu"
            self.cleanup_ui_widgets()
            self.update_state("app_details")

        def exit_available_menu():
            self.available_menu_position = 0
            self.cleanup_ui_widgets()
            self.update_state("available_categories_menu")

        self.available_menu = Menu(
            self,
            menu_items=[app["manifest"]["app"]["name"] for app in self._filtered_apps],
            position=self.available_menu_position,
            info_items=[
                app["manifest"]["metadata"]["description"]
                for app in self._filtered_apps
            ],
            select_handler=on_select,
            back_handler=exit_available_menu,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def prepare_search_results_menu(self):
        """Build menu showing search results."""

        def on_select(_, i):
            self.details_app = self._search_results[i]
            self._app_details_return_state = "search_results"
            self.cleanup_ui_widgets()
            self.update_state("app_details")

        def exit_search_results():
            self._search_results = None
            self.cleanup_ui_widgets()
            self.update_state("main_menu")

        self.search_results_menu = Menu(
            self,
            menu_items=[app["manifest"]["app"]["name"] for app in self._search_results],
            info_items=[
                app["manifest"]["metadata"]["description"]
                for app in self._search_results
            ],
            select_handler=on_select,
            back_handler=exit_search_results,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def prepare_app_details(self):
        def on_install():
            app_to_install = self.details_app
            self.details_app = None
            self.cleanup_ui_widgets()
            self.to_install_app = app_to_install
            self.update_state("installing_app")

        def on_back():
            return_state = self._app_details_return_state or "available_menu"
            self.details_app = None
            self._app_details_return_state = None
            self.cleanup_ui_widgets()
            self.update_state(return_state)

        self.app_details = AppDetails(
            self,
            self.details_app,
            install_handler=on_install,
            back_handler=on_back,
        )

    def _prepare_update_detail(self):
        """Prepare the update detail view showing version comparison."""
        ia, store_entry = self._update_detail_app

        def on_update():
            self._update_detail_app = None
            self.cleanup_ui_widgets()
            if store_entry:
                self.to_install_app = store_entry
                self.update_state("installing_app")
            else:
                self.update_state("update_menu")

        def on_back():
            self._update_detail_app = None
            self.cleanup_ui_widgets()
            self.update_state("update_menu")

        self._update_detail_widget = UpdateDetailPanel(
            self,
            ia,
            store_entry,
            update_handler=on_update,
            back_handler=on_back,
        )

    def prepare_main_menu(self):
        def on_cancel():
            self.cleanup_ui_widgets()
            self.minimise()

        def on_select(value, idx):
            self.cleanup_ui_widgets()
            if value == CODE_INSTALL:
                self.codeinstall = CodeInstall(
                    install_handler=lambda id: self.handle_code_input(id), app=self
                )
                self.update_state("code_install_input")
            elif value == AVAILABLE:
                self.update_state("available_categories_menu")
            elif value == SEARCH:
                self.update_state("search_input")
            elif value == CAPABILITIES:
                self.update_state("capabilities_menu")
            elif value == INSTALLED:
                self.update_state("installed_menu")
            elif value == UPDATE:
                self._start_update_check()

        menu_items = [AVAILABLE, SEARCH, CAPABILITIES, CODE_INSTALL, UPDATE]
        if len(list_all_apps()) > 0:
            menu_items.append(INSTALLED)

        self.menu = Menu(
            self,
            menu_items=menu_items,
            select_handler=on_select,
            back_handler=on_cancel,
        )

    def prepare_update_menu(self):
        def on_cancel():
            self.cleanup_ui_widgets()
            self._update_all_list = []
            self._update_phase = 0
            self._update_unmatched = []
            self.update_state("main_menu")

        def on_select(value, idx):
            self.cleanup_ui_widgets()
            if idx == 0 and self._update_updatable:
                self._update_install_queue = [
                    se
                    for (ia, se) in self._update_all_list
                    if se and se["manifest"]["metadata"]["version"] != ia["version"]
                ]
                self._update_all_in_progress = True
                self._install_next_from_queue()
            else:
                offset = 1 if self._update_updatable else 0
                real_idx = idx - offset
                ia, store_entry = self._update_all_list[real_idx]
                self._update_detail_app = (ia, store_entry)
                self.update_state("update_detail")

        menu_items = []
        info_items = []
        self._update_updatable = False

        updatable = []
        current = []
        for ia, store_entry in self._update_all_list:
            if store_entry:
                latest = store_entry["manifest"]["metadata"]["version"]
                if latest != ia["version"]:
                    updatable.append((ia, store_entry))
                else:
                    current.append((ia, store_entry))
            else:
                current.append((ia, None))

        self._update_all_list = updatable + current

        if updatable:
            self._update_updatable = True
            menu_items.append("\u21bb Update All")
            n = len(updatable)
            info_items.append(f"{n} app{'s' if n > 1 else ''} to update")

        for ia, store_entry in self._update_all_list:
            if store_entry:
                latest = store_entry["manifest"]["metadata"]["version"]
                if latest != ia["version"]:
                    menu_items.append(f"{ia['name']}  {ia['version']} \u2192 {latest}")
                    info_items.append("Update available")
                else:
                    menu_items.append(f"{ia['name']}  {ia['version']}")
                    info_items.append("Up to date")
            else:
                menu_items.append(f"{ia['name']}  {ia['version']}")
                info_items.append("Not in store")

        self.update_menu = Menu(
            self,
            menu_items=menu_items,
            info_items=info_items,
            select_handler=on_select,
            back_handler=on_cancel,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def prepare_installed_menu(self):
        def on_cancel():
            self.cleanup_ui_widgets()
            self.update_state("main_menu")

        def on_select(value, idx):
            self.uninstall_app(value)
            self.cleanup_ui_widgets()
            self.update_state("main_menu")

        installed_apps = list_all_apps()

        self.installed_menu = Menu(
            self,
            menu_items=[app["name"] for app in installed_apps],
            select_handler=on_select,
            back_handler=on_cancel,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def uninstall_app(self, app):
        user_apps = list_all_apps()
        selected_app = list(filter(lambda x: x["name"] == app, user_apps))
        if len(selected_app) == 0:
            raise RuntimeError(f"app not found: {app}")
        if len(selected_app) > 1:
            raise RuntimeError(f"duplicate app found: {app}")
        else:
            selected_app = selected_app[0]
        selected_app_module = selected_app["path"]
        selected_app_fs_path = "/" + "/".join(selected_app_module.split(".")[0:-1])
        print(f"Selected app fs path: {selected_app_fs_path}")
        shutil.rmtree(selected_app_fs_path)
        eventbus.emit(InstallNotificationEvent())
        machine.reset()

    def error_screen(self, ctx, message):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        lines = message.split("\n")
        start_y = -len(lines) * ctx.font_size / 2

        for i, line in enumerate(lines):
            ctx.gray(1).move_to(0, start_y + i * ctx.font_size).text(line)
        ctx.restore()

    async def run(self, render_update):
        last_time = time.ticks_ms()
        await render_update()
        while True:
            cur_time = time.ticks_ms()
            delta_ticks = time.ticks_diff(cur_time, last_time)
            await self.main_loop(delta_ticks, render_update)
            await render_update()
            last_time = cur_time

    async def main_loop(self, delta, render_update):
        bg.update(delta)
        if self.state == "init":
            print("App Store ready for on-demand loading")
            self.update_state("main_menu")
        elif self.state == "category_apps_received":
            self.handle_category_apps()
        elif self.state == "capability_apps_received":
            self.handle_capability_apps()
        elif self.state == "code_lookup_received":
            self.handle_code_lookup_response()
        elif self.state == "search_input":
            dialog = TextDialog("Search apps by name", self)
            result = await dialog.run(render_update)
            if result and result.strip():
                self._search_query = result.strip()
                self.update_state("searching")
            else:
                self.update_state("main_menu")
        elif self.state == "searching":
            gc.collect()
            try:
                url = _build_app_url("/apps", {"q": self._search_query})
                print(f"Searching apps: {url}")
                self.response = await async_helpers.unblock(get, render_update, url)
                status = getattr(self.response, "status_code", 0)
                if status == 200:
                    self._search_results = self.response.json().get("items", [])
                    if self._search_results:
                        self.update_state("search_results")
                    else:
                        eventbus.emit(
                            ShowNotificationEvent(
                                f"No results for '{self._search_query}'"
                            )
                        )
                        self.update_state("main_menu")
                else:
                    print(f"Search returned HTTP {status}")
                    self.update_state("no_index")
                    self._last_error = f"HTTP {status}"
            except Exception as e:
                print(f"Search error: {e}")
                self._last_error = str(e)[:40]
                self.update_state("no_index")
        elif self.state == "main_menu" and not self.menu:
            self.prepare_main_menu()
        elif self.state == "search_results" and not self.search_results_menu:
            self.prepare_search_results_menu()
        elif (
            self.state == "available_categories_menu"
            and not self.available_categories_menu
        ):
            self.prepare_available_categories_menu()
        elif self.state == "available_menu" and not self.available_menu:
            self.prepare_available_menu()
        elif self.state == "app_details" and not self.app_details:
            self.prepare_app_details()
        elif self.state == "loading_capabilities":
            gc.collect()
            try:
                self.available_capabilities = await async_helpers.unblock(
                    _get_available_capabilities, render_update
                )
            except Exception as e:
                print(f"Capabilities detection error: {e}")
                self.available_capabilities = {}
            self.update_state("capabilities_menu")
        elif self.state == "capabilities_menu" and not self.capabilities_menu:
            self._build_capabilities_menu()
        elif self.state == "capability_apps_menu" and not self.capability_apps_menu:
            self.prepare_capability_apps_menu()
        elif self.state == "installed_menu" and not self.installed_menu:
            self.prepare_installed_menu()
        elif self.state == "update_menu" and not self.update_menu:
            self.prepare_update_menu()
        elif self.state == "update_detail" and not self._update_detail_widget:
            self._prepare_update_detail()
        elif self.state == "checking_updates":
            gc.collect()
            if self._update_phase == 0:
                codes = list(self._update_code_map.keys())
                if codes:
                    try:
                        url = _build_app_url("/apps", {"codes": ",".join(codes)})
                        print(f"Fetching updates for {len(codes)} codes: {url}")
                        self.response = await async_helpers.unblock(
                            get, render_update, url
                        )
                        status = getattr(self.response, "status_code", 0)
                        if status == 200:
                            items = self.response.json().get("items", [])
                            for item in items:
                                code = item.get("code")
                                if code and code in self._update_code_map:
                                    for ia in self._update_code_map[code]:
                                        self._update_results[ia["folder"]] = item
                                        _store_app_code(
                                            ia.get("app_dir", APP_INSTALL_DIR),
                                            ia["folder"],
                                            code,
                                        )
                        else:
                            print(f"[AppStore] Batch code lookup: HTTP {status}")
                    except Exception as e:
                        print(f"[AppStore] Batch code lookup error: {e}")
                self._update_unmatched = [
                    ia
                    for ia in self._update_installed_apps
                    if ia["folder"] not in self._update_results
                ]
                self._update_phase = 1
            elif self._update_phase == 1:
                if self._update_unmatched:
                    ia = self._update_unmatched.pop(0)
                    name = ia.get("name", "")
                    folder = ia.get("folder", "")
                    app_dir = ia.get("app_dir", APP_INSTALL_DIR)
                    manifest = load_manifest(app_dir, folder)
                    if not manifest:
                        for d in [BG_DIR, PAT_DIR] + APP_DIR:
                            manifest = load_manifest(d, folder)
                            if manifest:
                                app_dir = d
                                break
                    try:
                        url = _build_app_url("/apps", {"q": name})
                        print(f"Searching for unmatched app '{name}': {url}")
                        self.response = await async_helpers.unblock(
                            get, render_update, url
                        )
                        status = getattr(self.response, "status_code", 0)
                        if status == 200:
                            items = self.response.json().get("items", [])
                            for item in items:
                                item_name = (
                                    item.get("manifest", {})
                                    .get("app", {})
                                    .get("name", "")
                                )
                                if item_name == name:
                                    self._update_results[folder] = item
                                    code = item.get("code")
                                    if code:
                                        ia["app_dir"] = app_dir
                                        _store_app_code(app_dir, folder, code)
                                    break
                        else:
                            print(f"[AppStore] Name search '{name}': HTTP {status}")
                    except Exception as e:
                        print(f"[AppStore] Name search error for '{name}': {e}")
                else:
                    self._update_phase = 2
            else:
                self._update_all_list = []
                for ia in self._update_installed_apps:
                    folder = ia.get("folder", "")
                    store_entry = self._update_results.get(folder)
                    self._update_all_list.append((ia, store_entry))
                self.update_state("update_menu")
        elif self.state == "refreshing_category_apps":
            gc.collect()
            try:
                url = _build_app_url("/apps", {"category": [self.category_filter]})
                print(f"Fetching category apps from: {url}")
                self.category_apps_response = await async_helpers.unblock(
                    get, render_update, url
                )
            except Exception as e:
                print(f"Category fetch network error: {e}")
                self._last_error = str(e)[:40]
                self.update_state("no_index")
            else:
                self.update_state("category_apps_received")
        elif self.state == "refreshing_capability_apps":
            gc.collect()
            try:
                url = _build_app_url("/apps", self._capability_params)
                print(f"Fetching capability apps from: {url}")
                self.capability_apps_response = await async_helpers.unblock(
                    get, render_update, url
                )
            except Exception as e:
                print(f"Capability fetch network error: {e}")
                self._last_error = str(e)[:40]
                self.update_state("no_index")
            else:
                self.update_state("capability_apps_received")
        elif self.state == "looking_up_code":
            gc.collect()
            try:
                url = _build_app_url(f"/apps/{self._lookup_code}")
                print(f"Looking up app by code: {url}")
                self.response = await async_helpers.unblock(get, render_update, url)
            except Exception as e:
                print(f"Code lookup network error: {e}")
                eventbus.emit(ShowNotificationEvent(f"Network error:\n{str(e)[:40]}"))
                self._last_error = str(e)[:40]
                self.update_state("no_index")
            else:
                self.update_state("code_lookup_received")
        elif self.state == "installing_app":
            # Wait one cycle so the installation screen is drawn
            success = await async_helpers.unblock(
                self.install_app, render_update, self.to_install_app
            )
            self.to_install_app = None
            if not success:
                self._update_install_queue = []
                self._update_all_in_progress = False
            elif self._update_install_queue:
                self._install_next_from_queue()
            elif self._update_all_in_progress:
                self._update_all_in_progress = False
                self._update_all_list = []
                self._update_results = {}
                self._update_phase = 0
                self._update_unmatched = []
                eventbus.emit(InstallNotificationEvent())
                eventbus.emit(ShowNotificationEvent("All updates installed!"))
                eventbus.emit(EmotePositiveEvent())
                self.update_state("main_menu")
            else:
                eventbus.emit(InstallNotificationEvent())
                eventbus.emit(ShowNotificationEvent("Installed the app!"))
                eventbus.emit(EmotePositiveEvent())
                self.update_state("main_menu")
        if self.menu:
            self.menu.update(delta)
        if self.available_categories_menu:
            self.available_categories_menu.update(delta)
        if self.available_menu:
            self.available_menu.update(delta)
        if self.capabilities_menu:
            self.capabilities_menu.update(delta)
        if self.capability_apps_menu:
            self.capability_apps_menu.update(delta)
        if self.installed_menu:
            self.installed_menu.update(delta)
        if self.update_menu:
            self.update_menu.update(delta)
        if self.search_results_menu:
            self.search_results_menu.update(delta)

    def draw(self, ctx):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        bg.draw(ctx)
        if self.state == "main_menu" and self.menu:
            self.menu.draw(ctx)
        elif self.state == "main_menu" and not self.menu:
            self.error_screen(ctx, "Loading...")
        elif (
            self.state == "available_categories_menu" and self.available_categories_menu
        ):
            self.available_categories_menu.draw(ctx)
        elif (
            self.state == "available_categories_menu"
            and not self.available_categories_menu
        ):
            self.error_screen(ctx, "Loading...")
        elif self.state == "available_menu" and self.available_menu:
            self.available_menu.draw(ctx)
        elif self.state == "available_menu" and not self.available_menu:
            pass
        elif self.state == "search_results" and self.search_results_menu:
            self.search_results_menu.draw(ctx)
        elif self.state == "search_results" and not self.search_results_menu:
            self.error_screen(ctx, "Loading...")
        elif self.state == "app_details" and self.app_details:
            self.app_details.draw(ctx)
        elif self.state == "app_details" and not self.app_details:
            pass
        elif self.state == "loading_capabilities":
            self.error_screen(ctx, "Detecting\ncapabilities...")
        elif self.state == "capabilities_menu" and self.capabilities_menu:
            self.capabilities_menu.draw(ctx)
        elif self.state == "capabilities_menu" and not self.capabilities_menu:
            self.error_screen(ctx, "Loading...")
        elif self.state == "capability_apps_menu" and self.capability_apps_menu:
            self.capability_apps_menu.draw(ctx)
        elif self.state == "capability_apps_menu" and not self.capability_apps_menu:
            self.error_screen(ctx, "Loading...")
        elif self.state == "installed_menu" and self.installed_menu:
            self.installed_menu.draw(ctx)
        elif self.state == "installed_menu" and not self.installed_menu:
            self.error_screen(ctx, "Loading...")
        elif self.state == "update_menu" and self.update_menu:
            self.update_menu.draw(ctx)
        elif self.state == "update_menu" and not self.update_menu:
            self.error_screen(ctx, "Loading...")
        elif self.state == "update_detail" and self._update_detail_widget:
            self._update_detail_widget.draw(ctx)
        elif self.state == "update_detail" and not self._update_detail_widget:
            self.error_screen(ctx, "Loading...")
        elif self.state == "no_wifi":
            self.error_screen(ctx, "No Wi-Fi\nconnection")
        elif self.state == "checking_updates":
            if self._update_phase == 0:
                self.error_screen(ctx, "Checking\nfor updates...")
            else:
                remaining = len(self._update_unmatched)
                self.error_screen(ctx, f"Searching...\n{remaining} unmatched")
        elif self.state == "refreshing_category_apps":
            self.error_screen(ctx, f"Loading\n{self.category_filter}\napps...")
        elif self.state == "refreshing_capability_apps":
            self.error_screen(ctx, "Loading\ncapability\napps...")
        elif self.state == "looking_up_code":
            self.error_screen(ctx, "Looking up\napp code...")
        elif self.state == "searching":
            self.error_screen(ctx, f"Searching...\n{self._search_query}")
        elif self.state == "category_apps_received":
            self.error_screen(ctx, "Category\nreceived")
        elif self.state == "capability_apps_received":
            self.error_screen(ctx, "Capability\nreceived")
        elif self.state == "code_lookup_received":
            self.error_screen(ctx, "Code\nreceived")
        elif self.state == "search_input":
            pass
        elif self.state == "no_index":
            if self._last_error:
                self.error_screen(ctx, f"Error\n{self._last_error}")
            else:
                self.error_screen(ctx, "Index\nerror\n(press F for menu)")
        elif self.state == "install_oom":
            self.error_screen(ctx, "Out of memory\n(app too big?)")
        elif self.state == "code_install_input" and self.codeinstall:
            self.codeinstall.draw(ctx)
        elif self.state == "installing_app":
            if self.to_install_app:
                self.error_screen(
                    ctx, "Installing\n" + self.to_install_app["manifest"]["app"]["name"]
                )
            else:
                self.error_screen(ctx, "Installing...")
        elif self.state == "init":
            self.error_screen(ctx, "Loading...")
        else:
            self.error_screen(ctx, "Unknown error")
            print("Unknown error " + self.state)
        ctx.restore()

        self.draw_overlays(ctx)


class AppDetails:
    """Scrollable app detail page with an install option at the end."""

    def __init__(
        self,
        app: app.App,
        store_entry: dict,
        install_handler: Callable[[], Any],
        back_handler: Callable[[], Any],
    ):
        self.app = app
        self.install_handler = install_handler
        self.back_handler = back_handler
        self._cleaned_up = False

        manifest = store_entry.get("manifest", {})
        app_info = manifest.get("app", {})
        metadata = manifest.get("metadata", {})
        entry_id = store_entry.get("id", {})

        self.title = app_info.get("name") or entry_id.get("title", "Unknown app")
        self.author = (
            metadata.get("author")
            or metadata.get("maintainer")
            or entry_id.get("owner", "Unknown author")
        )
        self.description = metadata.get("description") or "No description provided."
        self.version = metadata.get("version", "")

        self._rows = None
        self._total_height = None
        self._max_scroll = None

        self.scroll = 0
        self._scroll_step = seven_pt * 1.1

        self._page_top = -75
        self._page_bottom = 80
        self._draw_bottom = 118

        eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def _at_end(self):
        return self._max_scroll is not None and self.scroll >= self._max_scroll

    def _scroll_down(self):
        if self._max_scroll is not None:
            self.scroll = min(self._max_scroll, self.scroll + self._scroll_step)

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["CONFIRM"] in event.button:
            if self._at_end():
                self._cleanup()
                self.install_handler()
        elif BUTTON_TYPES["CANCEL"] in event.button:
            self._cleanup()
            self.back_handler()
        elif BUTTON_TYPES["UP"] in event.button:
            self.scroll = max(0, self.scroll - self._scroll_step)
        elif BUTTON_TYPES["DOWN"] in event.button:
            self._scroll_down()

    def _cleanup(self):
        if not self._cleaned_up:
            eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)
            self._cleaned_up = True

    def _build_rows(self, ctx):
        rows = []

        title_lines = wrap_text(ctx, self.title, twelve_pt, width=170)
        for line in title_lines:
            rows.append((line, twelve_pt, "label", 0))

        author_lines = wrap_text(ctx, f"by {self.author}", seven_pt, width=175)
        for line in author_lines:
            rows.append((line, seven_pt, "button_background", 0))
        if self.version:
            rows.append((f"v{self.version}", seven_pt, "button_background", 0))
        if rows:
            text, size, colour, _ = rows[-1]
            rows[-1] = (text, size, colour, 6)

        for line in wrap_text(ctx, self.description, seven_pt, width=175):
            rows.append((line, seven_pt, "label", 0))
        text, size, colour, _ = rows[-1]
        rows[-1] = (text, size, colour, 6)

        rows.append(("Install now", seven_pt, None, 0))

        self._rows = rows
        self._total_height = sum(size * 1.1 + gap for (_, size, _, gap) in rows)
        page_height = self._page_bottom - self._page_top
        self._max_scroll = max(0, self._total_height - page_height)
        self.scroll = min(self.scroll, self._max_scroll)

    @staticmethod
    def _draw_download_icon(ctx, cx, cy):
        """Draw a small download glyph."""
        ctx.begin_path()
        ctx.rectangle(cx - 1.5, cy - 8, 3, 6).fill()
        ctx.begin_path()
        ctx.move_to(cx - 5, cy - 3)
        ctx.line_to(cx + 5, cy - 3)
        ctx.line_to(cx, cy + 3)
        ctx.close_path()
        ctx.fill()
        ctx.begin_path()
        ctx.rectangle(cx - 6, cy + 5, 12, 2.5).fill()

    def draw(self, ctx):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        if self._rows is None:
            self._build_rows(ctx)

        at_end = self._at_end()
        y = self._page_top - self.scroll

        for text, size, colour, gap in self._rows:
            row_height = size * 1.1
            center = y + row_height / 2
            if -84 <= center and center - row_height / 2 <= self._draw_bottom:
                if colour is None:
                    set_color(ctx, "active_menu_item" if at_end else "label")
                    ctx.font_size = size
                    ctx.move_to(0, center).text(text)
                    icon_offset = ctx.text_width(text) / 2 + 14
                    self._draw_download_icon(ctx, -icon_offset, center)
                    self._draw_download_icon(ctx, icon_offset, center)
                else:
                    set_color(ctx, colour)
                    ctx.font_size = size
                    ctx.move_to(0, center).text(text)
            y += row_height + gap

        ctx.restore()


class UpdateDetailPanel:
    """Simple detail panel showing installed vs latest version for an app."""

    def __init__(
        self,
        app: app.App,
        installed_app: dict,
        store_entry: dict,
        update_handler: Callable[[], Any],
        back_handler: Callable[[], Any],
    ):
        self.app = app
        self.update_handler = update_handler
        self.back_handler = back_handler
        self._cleaned_up = False

        self.name = installed_app.get("name", "Unknown")
        self.installed_version = installed_app.get("version", "0.0.0")

        if store_entry:
            manifest = store_entry.get("manifest", {})
            metadata = manifest.get("metadata", {})
            self.latest_version = metadata.get("version", "?")
            self.author = (
                metadata.get("author")
                or metadata.get("maintainer")
                or store_entry.get("id", {}).get("owner", "?")
            )
            self.description = metadata.get("description") or ""
            self._has_update = self.latest_version != self.installed_version
        else:
            self.latest_version = "?"
            self.author = "?"
            self.description = ""
            self._has_update = False

        eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["CONFIRM"] in event.button:
            if self._has_update:
                self._cleanup()
                self.update_handler()
        elif BUTTON_TYPES["CANCEL"] in event.button:
            self._cleanup()
            self.back_handler()

    def _cleanup(self):
        if not self._cleaned_up:
            eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)
            self._cleaned_up = True

    def draw(self, ctx):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        ctx.font_size = twelve_pt
        set_color(ctx, "label")
        ctx.move_to(0, -50).text(self.name)

        if self.author != "?":
            ctx.font_size = seven_pt
            set_color(ctx, "button_background")
            ctx.move_to(0, -32).text(f"by {self.author}")

        ctx.font_size = ten_pt
        set_color(ctx, "label")
        ctx.move_to(0, -5).text(f"Installed: {self.installed_version}")

        ctx.font_size = ten_pt
        if self.latest_version == "?":
            set_color(ctx, "button_background")
            ctx.move_to(0, 16).text("Not found in store")
        elif self._has_update:
            set_color(ctx, "active_menu_item")
            ctx.move_to(0, 16).text(f"Latest: {self.latest_version}")

            ctx.font_size = seven_pt
            set_color(ctx, "label")
            ctx.move_to(0, 38).text("CONFIRM to update")
        else:
            set_color(ctx, "button_background")
            ctx.move_to(0, 16).text(f"Latest: {self.latest_version}")
            ctx.font_size = seven_pt
            set_color(ctx, "label")
            ctx.move_to(0, 38).text("Up to date")

        ctx.restore()


class CodeInstall:
    def __init__(self, install_handler: Callable[[str], Any], app: app.App):
        self.app = app
        self.install_handler = install_handler
        self.state = "input"
        self.id: str = ""
        self.active_button = None
        self.activation_counter = 0

        self.interlopers = {
            "characters": ["shark", "spider"],
            "offsets": {"min": -60, "max": 40},
            "size": {"min": 30, "max": 50},
        }

        self.reset_interloper()

        self.include_interloper = random() > 0.9

        eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def reset_interloper(self):
        """Reset the interloper."""
        self.interloper_character = choice(self.interlopers["characters"])
        self.interloper_size = randint(
            self.interlopers["size"]["min"],
            self.interlopers["size"]["max"],
        )

        interloper_off_screen = randint(
            self.interlopers["offsets"]["min"], -self.interloper_size
        )
        interloper_on_screen = randint(0, self.interlopers["offsets"]["max"])

        self.interloper_offsets = (
            list(range(interloper_off_screen, interloper_on_screen, 1))
            + [interloper_on_screen] * 10
            + list(range(interloper_on_screen, interloper_off_screen, -1))
        )
        self.interloper_offset_index = 0

        self.interloper_rotation = random() * 2 * pi

    def _handle_buttondown(self, event: ButtonDownEvent):
        kbd_button = event.button.find_parent_in_group("Keyboard")
        original_id = self.id

        if FRONTBOARD_BUTTON_TYPES["A"] in event.button:
            self.id += "0"
        elif FRONTBOARD_BUTTON_TYPES["B"] in event.button:
            self.id += "1"
        elif FRONTBOARD_BUTTON_TYPES["C"] in event.button:
            self.id += "2"
        elif FRONTBOARD_BUTTON_TYPES["D"] in event.button:
            self.id += "3"
        elif FRONTBOARD_BUTTON_TYPES["E"] in event.button:
            self.id += "4"
        elif FRONTBOARD_BUTTON_TYPES["F"] in event.button:
            self.id += "5"
        elif kbd_button is not None and kbd_button.name in "012345":
            self.id += kbd_button.name

        if original_id == self.id:
            return

        self.active_button = int(self.id[-1])
        self.activation_counter = 3

        if len(self.id) == 8:
            self._cleanup()
            self.install_handler(self.id)

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)

    def draw(self, ctx):
        if self.include_interloper:
            self.draw_interloper(ctx)

        self.draw_numbers(ctx)

        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.font_size = ten_pt
        ctx.gray(1).move_to(0, -1.5 * ten_pt).text("Enter code:")
        ctx.font_size = sixteen_pt
        ctx.gray(1).move_to(0, 0).text(self.id)
        ctx.restore()

    def draw_interloper(self, ctx):
        """Spider, maybe?"""
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.rotate(self.interloper_rotation)
        ctx.rgba(1, 1, 1, 0.3)
        ctx.move_to(-120 + self.interloper_offsets[self.interloper_offset_index], 0)
        ctx.font_size = self.interloper_size
        ctx.text(symbols[self.interloper_character])
        ctx.rotate(-self.interloper_rotation)

        self.interloper_offset_index += 1
        if self.interloper_offset_index >= len(self.interloper_offsets):
            self.reset_interloper()

    def draw_numbers(self, ctx):
        """Draw indicator numbers."""
        for i in range(6):
            triangle_type = "regular"
            text_colour = "button_text"
            if i == self.active_button:
                triangle_type = "active"
                text_colour = "active_button_text"
                if self.activation_counter > 0:
                    self.activation_counter -= 1

                else:
                    self.active_button = None

            self.draw_triangle(ctx, key=triangle_type)

            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
            ctx.font_size = seven_pt
            set_color(ctx, text_colour)
            ctx.move_to(0, -100)
            ctx.text(str(i))
            ctx.rotate(radians(60))

    def draw_triangle(self, ctx, key="regular"):
        """Draw a pointer."""
        triangles = {
            "regular": {"colour": "button_background", "size": 40},
            "active": {"colour": "active_button_background", "size": 50},
        }
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        set_color(ctx, triangles[key]["colour"])
        ctx.move_to(0, -97)
        ctx.font_size = triangles[key]["size"]
        ctx.text(symbols["pointing_triangles"]["up"])


def install_app(app):
    try:
        ## This is fine to block because we only call it from background_update
        print("GC")
        gc.collect()

        print(f"Getting {app['tarballUrl']}")
        tarball = get(app["tarballUrl"])

        # TODO: Investigate using deflate.DeflateIO instead. Can't do it now
        # because it's not available in the simulator.
        print("Decompressing")
        tar = gzip.decompress(tarball.content)
        gc.collect()
        tar_bytesio = io.BytesIO(tar)

        print("Validating")
        prefix = find_app_root_dir(TarFile(fileobj=tar_bytesio)).rstrip("/")
        tar_bytesio.seek(0)
        print(f"Found app prefix: {prefix}")
        app_py_info = find_app_py_file(prefix, TarFile(fileobj=tar_bytesio))
        print(f"Found app.py at: {app_py_info.name}")
        tar_bytesio.seek(0)

        # TODO: Check we have enough storage in advance
        # TODO: Does the app already exist? Delete it
        if get_first_category(app["manifest"]["app"]) == "Background":
            TARGET_DIR = "/backgrounds"
        elif get_first_category(app["manifest"]["app"]) == "Pattern":
            TARGET_DIR = "/pattern"
        else:
            TARGET_DIR = APP_INSTALL_DIR
        # Make sure apps dir exists
        try:
            os.mkdir(TARGET_DIR)
        except OSError:
            pass

        app_module_name = "_".join([app["id"]["owner"], app["id"]["title"]]).replace(
            "-", "_"
        )

        has_tildagon_json = False

        t = TarFile(fileobj=tar_bytesio)
        for i in t:
            if i:
                if not i.name.startswith(prefix):
                    continue
                if i.type == DIRTYPE:
                    dirname = f"{TARGET_DIR}/{i.name}"
                    dirname = dirname.replace(prefix, app_module_name, 1)
                    print(f"Dirname: {dirname}")
                    if not dir_exists(dirname):
                        try:
                            print(f"Creating {dirname}")
                            os.mkdir(dirname.rstrip("/"))
                        except OSError:
                            print(f"Failed to create {dirname}")
                            pass
                else:
                    filename = f"{TARGET_DIR}/{i.name}"
                    filename = filename.replace(prefix, app_module_name, 1)
                    print(f"Filename: {filename}")

                    # Track whether the tarball includes a tildagon.json
                    if i.name == f"{prefix}/tildagon.json":
                        has_tildagon_json = True

                    f = t.extractfile(i)
                    if f:
                        with open(filename, "wb") as file:
                            while data := f.read():
                                file.write(data)

        # Remove tildagon.toml if it was in the tarball (not used)
        toml_path = f"{TARGET_DIR}/{app_module_name}/tildagon.toml"
        try:
            os.remove(toml_path)
            print(f"Removed unused {toml_path}")
        except OSError:
            pass

        # Write the app store manifest as tildagon.json if the tarball didn't include one
        if not has_tildagon_json:
            tildagon_json_path = f"{TARGET_DIR}/{app_module_name}/tildagon.json"
            print(f"Writing manifest to {tildagon_json_path}")
            with open(tildagon_json_path, "w+") as f:
                json.dump(app["manifest"], f)

        internal_manifest = {
            "name": app["manifest"]["app"]["name"],
            "hidden": False,
            "version": app["manifest"]["metadata"]["version"],
        }
        # Store the app code if available
        app_code = app.get("code")
        if app_code:
            internal_manifest["app_code"] = app_code
            # Also store service/owner/title for future reference
            app_id = app.get("id", {})
            if app_id.get("service"):
                internal_manifest["app_service"] = app_id["service"]
            if app_id.get("owner"):
                internal_manifest["app_owner"] = app_id["owner"]
            if app_id.get("title"):
                internal_manifest["app_title"] = app_id["title"]
        json_path = f"{TARGET_DIR}/{app_module_name}/metadata.json"
        print(f"Json path: {json_path}")
        with open(json_path, "w+") as internal_manifest_file_handler:
            json.dump(internal_manifest, internal_manifest_file_handler)

    except MemoryError as e:
        gc.collect()
        raise e
    except Exception as e:
        print(e)
        raise e


def find_app_root_dir(tar):
    print("Finding root dir...")
    root_dir = None
    for i, f in enumerate(tar):
        print(f"prefix: {i}, name: {f.name}")
        # Normalise directory names between MicroPython's tarfile which uses
        # "dir/" and Python's tarfile which uses "dir"
        name = f.name.rstrip("/")
        slash_count = len(name.split("/"))
        if slash_count == 1 and f.isdir():
            if root_dir is None:
                root_dir = name + "/"
            else:
                raise ValueError("More than one root directory found in app tarball")
    if root_dir is None:
        raise ValueError("No root dir in tarball")
    return root_dir


def find_app_py_file(prefix, tar) -> tarfile.TarInfo:
    print("Finding app.py...")
    found_app_py = False
    expected_path = f"{prefix}/app.py"
    alternative_path = f"{prefix}/app.mpy"
    app_py_info = None

    for i, f in enumerate(tar):
        print(f"prefix: {i}, name: {f.name}")
        if f.name == expected_path or f.name == alternative_path:
            found_app_py = True
            app_py_info = f
    if not found_app_py:
        raise ValueError(
            f"No app.py found in tarball, expected location: {expected_path}"
        )
    return app_py_info
