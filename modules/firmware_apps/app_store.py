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

try:
    import hashlib

    _have_hashlib = True
except ImportError:
    _have_hashlib = False


def get_first_category(manifest):
    """Extract the first category from an app manifest.

    Categories can be a string or a list of strings. This always returns a
    single string (the first element if it's a list).
    """
    category = manifest.get("category")
    if isinstance(category, list):
        return category[0] if category else None
    return category


def _version_gt(v1, v2):
    """Compare two semver-like version strings. Returns True if v1 > v2."""
    return v1.split(".") > v2.split(".")


def dir_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) != 0
    except OSError:
        return False


APP_STORE_API_BASE = "https://apps.badge.emfcamp.org/v1"
APP_STORE_LISTING_URL = f"{APP_STORE_API_BASE}/apps"


def _quote(s):
    """Minimal URL-encoding for query parameter values."""
    # Hex-encode chars that are not unreserved per RFC 3986
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    res = []
    for c in str(s):
        if c in safe:
            res.append(c)
        else:
            res.append("%%%02X" % ord(c))
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
    """Compute an 8-character app code from service, owner, and title.

    This mirrors the TypeScript implementation in TildagonAppReleaseIdentifier.
    Returns an 8-character string of digits '0'-'4', or None if hashlib is
    unavailable.
    """
    if not _have_hashlib:
        return None
    payload = service + owner + title
    h = hashlib.md5(payload.encode())
    digest = h.digest()
    code = "".join(chr(ord("0") + (b % 5)) for b in digest[:8])
    return code


def _get_app_code_from_metadata(app_dir, folder_name):
    """Try to retrieve a stored app code from metadata.json."""
    info = load_info(app_dir, folder_name)
    return info.get("app_code")


def _find_app_codes(app_dir, folder_name, manifest):
    """Find all candidate app codes for an installed app.

    Returns a list of candidate code strings (may be empty).
    """
    # 1. Check stored code
    stored = _get_app_code_from_metadata(app_dir, folder_name)
    if stored:
        return [stored]

    if not _have_hashlib:
        return []

    manifest_app = manifest.get("app", {})
    manifest_name = manifest_app.get("name", "")
    manifest_author = manifest.get("metadata", {}).get("author", "")

    # Build candidate (service, owner, title) triples to try
    candidates = []

    parts = folder_name.split("_")

    # If we have an author, try it as owner with various titles
    if manifest_author:
        candidates.append((manifest_author, folder_name))
        if manifest_name and manifest_name != folder_name:
            candidates.append((manifest_author, manifest_name))
        if len(parts) >= 2:
            candidates.append((manifest_author, parts[-1]))

    # Try splits of the folder name
    if len(parts) >= 2:
        for split_idx in range(1, len(parts)):
            owner = "_".join(parts[:split_idx])
            title = "_".join(parts[split_idx:])
            candidates.append((owner, title))
    else:
        candidates.append(("emfcamp", folder_name))
        candidates.append(("badge", folder_name))

    # Also try with the manifest name as title if different
    if manifest_name and manifest_name != folder_name:
        if manifest_author:
            pass  # already added above
        for service in APP_STORE_SERVICES:
            candidates.append(
                (service, manifest_name)
            )  # service as owner? weird but try

    # Try each candidate with both services, collect all codes
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
    """Store the app code in metadata.json for future use."""
    import json

    metadata_path = f"{app_dir}/{folder_name}/metadata.json"
    try:
        with open(metadata_path, "r") as f:
            metadata = json.loads(f.read())
    except Exception:
        metadata = {}
    if metadata.get("app_code") != code:
        metadata["app_code"] = code
        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)
        except Exception as e:
            print(f"[AppStore] Failed to store app code: {e}")


def _get_available_capabilities():
    """Detect capabilities currently available on this badge.

    Returns a dict with keys like 'frontboard', 'hexpansions', 'capabilities'
    that can be used to filter apps in the store.
    """
    caps = {}

    # Detect frontboard
    try:
        from frontboards.utils import detect_frontboard

        fb = detect_frontboard()
        if (fb & 0xFF00) == 0x2600:
            caps["frontboard"] = "2026 Frontboard"
        elif (fb & 0xFF00) == 0x2400:
            caps["frontboard"] = "2024 Frontboard"
    except Exception:
        pass

    # Detect hexpansions
    try:
        from system.hexpansion.app import _hexpansion_manager

        for port, header in _hexpansion_manager.hexpansion_headers.items():
            if header is not None:
                caps.setdefault("hexpansions", []).append(
                    {"vid": hex(header.vid), "pid": hex(header.pid)}
                )
    except Exception:
        pass

    # Detect capabilities provided by installed apps
    try:
        from system.capabilities.utils import list_capabilities

        for entry in list_capabilities():
            for cap in entry.get("capabilities", []):
                caps.setdefault("capabilities", []).append(cap)
    except Exception:
        pass

    return caps


CODE_INSTALL = "Use Code"
AVAILABLE = "Browse Apps"
CAPABILITIES = "By Capability"
INSTALLED = "Uninstall"
UPDATE = "Update Apps"

# Hardcoded app store categories (no longer fetched from the full index)
APP_STORE_CATEGORIES = [
    "Badge",
    "Music",
    "Media",
    "Apps",
    "Games",
    "Background",
    "Pattern",
]

# Services that may host apps (used when computing app codes)
APP_STORE_SERVICES = ["github", "codeberg"]


def list_apps(dir, callable):
    with PerfTimer("List user apps"):
        apps = []
        try:
            contents = os.listdir(dir)
        except OSError:
            # directory doesn't exist
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
        self._filtered_apps = []  # Apps from filtered API calls (category/capability)
        self.apps_with_updates = []
        self.app_categories = APP_STORE_CATEGORIES  # Hardcoded, no longer from index
        self.category_filter = None
        self.available_capabilities = None  # Detected badge capabilities
        self.category_apps_response = None  # Response for per-category fetch
        self.capability_apps_response = None  # Response for per-capability fetch
        self.to_install_app = None
        self.tarball = None
        self.wait_one_cycle = False
        self._lookup_code = None  # Code being looked up via API
        self._capability_params = None  # Params for capability-filtered API call
        self._last_error = None  # Last error message for display
        # Update-check state
        self._update_code_map = {}  # code -> list of installed app dicts
        self._update_results = {}  # folder_name -> app store entry
        self._update_all_list = []  # list of (installed_app, store_entry_or_None) tuples
        self._update_install_queue = []  # queue of apps to install for "Update All"
        self._update_detail_app = None  # app being viewed in detail
        self._update_detail_widget = None  # UpdateDetailPanel widget
        self._update_phase = 0  # 0=code lookup, 1=name fallback, 2=done
        self._update_unmatched = []  # apps not found by code lookup

        # Register back-button handler for error states
        eventbus.on(ButtonDownEvent, self._handle_error_back, self)

    def _handle_error_back(self, event: ButtonDownEvent):
        """Handle back button in error states to return to main menu."""
        if self.state in (
            "no_wifi",
            "no_index",
            "install_oom",
            "checking_wifi",
        ):
            if FRONTBOARD_BUTTON_TYPES["F"] in event.button:
                self._last_error = None
                self.update_state("main_menu")

    def cleanup_ui_widgets(self):
        # Don't clean up during error states (no menus to clean)
        if self.state in ("no_wifi", "no_index", "install_oom"):
            return
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

    def _start_update_check(self):
        """Start checking installed apps for available updates.

        Computes codes for all installed apps and fetches them in a single
        batch request via the 'codes' parameter.
        """
        if not wifi.status():
            self.update_state("no_wifi")
            return
        installed_apps = list_all_apps()
        if not installed_apps:
            self.update_state("main_menu")
            eventbus.emit(ShowNotificationEvent("No apps installed"))
            return

        # Compute codes and build a mapping: code -> [list of installed apps]
        self._update_code_map = {}  # code -> list of ia dicts
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
                # Store corrected app_dir so _store_app_code writes to the right place
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
        try:
            install_app(app)
            self.update_state("main_menu")
            eventbus.emit(InstallNotificationEvent())
            eventbus.emit(ShowNotificationEvent("Installed the app!"))
            eventbus.emit(EmotePositiveEvent())
        except MemoryError:
            self.update_state("install_oom")
        except Exception as e:
            print(e)
            eventbus.emit(ShowNotificationEvent("Couldn't install app"))
            eventbus.emit(EmoteNegativeEvent())
            self.update_state("main_menu")

    def update_state(self, state):
        print(f"State Transition: '{self.state}' -> '{state}'")
        self.state = state

    def handle_code_input(self, code):
        print(f"Looking up app by code: {code}")
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
            self.get_category_apps(self.app_categories[i])
            self.cleanup_ui_widgets()

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
        """Build menu of available badge capabilities."""
        if self.available_capabilities is None:
            self.available_capabilities = _get_available_capabilities()

        caps = self.available_capabilities
        # Build a list of readable capability entries paired with API params
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

        for c in caps.get("capabilities", []):
            # Capability identifiers are URLs; show only the last path segment
            short = c.rstrip("/").rsplit("/", 1)[-1]
            self._capability_entries.append(
                (short, f"Capability: {c}", {"capability": [c]})
            )

        if not self._capability_entries:
            eventbus.emit(ShowNotificationEvent("No capabilities detected"))
            self.update_state("main_menu")
            return

        def on_select(_, i):
            self.get_capability_apps(self._capability_entries[i][2])
            self.cleanup_ui_widgets()

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

    def prepare_app_details(self):
        def on_install():
            app_to_install = self.details_app
            self.details_app = None
            self.cleanup_ui_widgets()
            self.to_install_app = app_to_install
            self.update_state("installing_app")

        def on_back():
            self.details_app = None
            self.cleanup_ui_widgets()
            self.update_state("available_menu")

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
            elif value == CAPABILITIES:
                self.update_state("capabilities_menu")
            elif value == INSTALLED:
                self.update_state("installed_menu")
            elif value == UPDATE:
                self._start_update_check()

        menu_items = [AVAILABLE, CAPABILITIES, CODE_INSTALL, UPDATE]
        if len(list_all_apps()) > 0:
            menu_items.append(
                INSTALLED
            )  # Only show uninstall option if there are installed apps (else a zero-length menu crashes)

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
                # "Update All" selected
                self._update_install_queue = [
                    se
                    for (ia, se) in self._update_all_list
                    if se
                    and _version_gt(
                        se["manifest"]["metadata"]["version"], ia["version"]
                    )
                ]
                self._install_next_from_queue()
            else:
                # App selected - show detail
                offset = 1 if self._update_updatable else 0
                real_idx = idx - offset
                ia, store_entry = self._update_all_list[real_idx]
                self._update_detail_app = (ia, store_entry)
                self.update_state("update_detail")

        def _version_gt(v1, v2):
            return v1.split(".") > v2.split(".")

        # Build menu items
        menu_items = []
        info_items = []
        self._update_updatable = False

        # First pass: find updatable apps
        updatable = []
        current = []
        for ia, store_entry in self._update_all_list:
            if store_entry:
                latest = store_entry["manifest"]["metadata"]["version"]
                if _version_gt(latest, ia["version"]):
                    updatable.append((ia, store_entry))
                else:
                    current.append((ia, store_entry))
            else:
                current.append((ia, None))

        # Reorder: updatable first, then current
        self._update_all_list = updatable + current

        if updatable:
            self._update_updatable = True
            menu_items.append("\u21bb Update All")
            n = len(updatable)
            info_items.append(f"{n} app{'s' if n > 1 else ''} to update")

        for ia, store_entry in self._update_all_list:
            if store_entry:
                latest = store_entry["manifest"]["metadata"]["version"]
                if _version_gt(latest, ia["version"]):
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
        elif self.state == "main_menu" and not self.menu:
            self.prepare_main_menu()
        elif (
            self.state == "available_categories_menu"
            and not self.available_categories_menu
        ):
            self.prepare_available_categories_menu()
        elif self.state == "available_menu" and not self.available_menu:
            self.prepare_available_menu()
        elif self.state == "app_details" and not self.app_details:
            self.prepare_app_details()
        elif self.state == "capabilities_menu" and not self.capabilities_menu:
            self.prepare_capabilities_menu()
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
            installed_apps = list_all_apps()
            if self._update_phase == 0:
                # Phase 0: batch code lookup
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
                # Gather unmatched apps for phase 1
                self._update_unmatched = [
                    ia
                    for ia in installed_apps
                    if ia["folder"] not in self._update_results
                ]
                self._update_phase = 1
            elif self._update_phase == 1:
                # Phase 1: name-based fallback for unmatched apps
                if self._update_unmatched:
                    ia = self._update_unmatched.pop(0)
                    name = ia.get("name", "")
                    folder = ia.get("folder", "")
                    # Determine correct app_dir for this app
                    app_dir = ia.get("app_dir", APP_INSTALL_DIR)
                    manifest = load_manifest(app_dir, folder)
                    if not manifest:
                        for d in [BG_DIR, PAT_DIR] + APP_DIR:
                            manifest = load_manifest(d, folder)
                            if manifest:
                                app_dir = d
                                break
                    try:
                        url = _build_app_url("/apps", {"search": name})
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
                # Phase 2: build results and show menu
                self._update_all_list = []
                for ia in installed_apps:
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
                # Network-level failure
                print(f"Category fetch network error: {e}")
                self._last_error = str(e)
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
                # Network-level failure
                print(f"Capability fetch network error: {e}")
                self._last_error = str(e)
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
                # Network-level failure (socket error, TLS, DNS, etc.)
                print(f"Code lookup network error: {e}")
                eventbus.emit(ShowNotificationEvent(f"Network error:\n{str(e)[:40]}"))
                self._last_error = str(e)
                self.update_state("no_index")
            else:
                self.update_state("code_lookup_received")
        elif self.state == "installing_app":
            # We wait one cycle after background_update is called to ensure the
            # installation screen is drawn
            await async_helpers.unblock(
                self.install_app, render_update, self.to_install_app
            )
            self.to_install_app = None
            # If there are more apps in the update queue, install the next one
            if self._update_install_queue:
                self._install_next_from_queue()
            else:
                self._update_install_queue = []
                self._update_all_list = []
                self._update_results = {}
                self._update_phase = 0
                self._update_unmatched = []
                eventbus.emit(InstallNotificationEvent())
                eventbus.emit(ShowNotificationEvent("All updates installed!"))
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
        elif self.state == "app_details" and self.app_details:
            self.app_details.draw(ctx)
        elif self.state == "app_details" and not self.app_details:
            pass
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
        elif self.state == "no_wifi":
            self.error_screen(ctx, "No Wi-Fi\nconnection")
        elif self.state == "checking_wifi":
            self.error_screen(ctx, "Checking\nWi-Fi connection")
        elif self.state == "checking_updates":
            if self._update_phase == 0:
                self.error_screen(ctx, "Checking\nfor updates...")
            else:
                remaining = len(self._update_unmatched)
                self.error_screen(ctx, f"Searching...\n{remaining} unmatched")
        elif self.state in ("wifi_init", "wifi_connecting"):
            self.error_screen(ctx, "Connecting\nWi-Fi...\n")
        elif self.state == "refreshing_category_apps":
            self.error_screen(ctx, f"Loading\n{self.category_filter}\napps...")
        elif self.state == "refreshing_capability_apps":
            self.error_screen(ctx, "Loading\ncapability\napps...")
        elif self.state == "looking_up_code":
            self.error_screen(ctx, "Looking up\napp code...")
        elif self.state == "index_received":
            self.error_screen(ctx, "Index\nreceived")
        elif self.state == "category_apps_received":
            self.error_screen(ctx, "Category\nreceived")
        elif self.state == "capability_apps_received":
            self.error_screen(ctx, "Capability\nreceived")
        elif self.state == "code_lookup_received":
            self.error_screen(ctx, "Code\nreceived")
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

        # rows of (text, font_size, colour, gap_after), built in draw()
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
            # rows straddling the bottom clip against the screen edge
            if -84 <= center and center - row_height / 2 <= self._draw_bottom:
                if colour is None:
                    # install row, highlighted once scrolled to the end
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
            self._has_update = _version_gt(self.latest_version, self.installed_version)
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

        # Title
        ctx.font_size = twelve_pt
        set_color(ctx, "label")
        ctx.move_to(0, -50).text(self.name)

        # Author
        if self.author != "?":
            ctx.font_size = seven_pt
            set_color(ctx, "button_background")
            ctx.move_to(0, -32).text(f"by {self.author}")

        # Installed version
        ctx.font_size = ten_pt
        set_color(ctx, "label")
        ctx.move_to(0, -5).text(f"Installed: {self.installed_version}")

        # Latest version
        ctx.font_size = ten_pt
        if self.latest_version == "?":
            set_color(ctx, "button_background")
            ctx.move_to(0, 16).text("Not found in store")
        elif self._has_update:
            set_color(ctx, "active_menu_item")
            ctx.move_to(0, 16).text(f"Latest: {self.latest_version}")

            # Update hint
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

        # 1 out of 10 times, we will draw some lads
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
            # We did not handle this button event, so bail now
            return

        self.active_button = int(self.id[-1])
        self.activation_counter = 3

        if len(self.id) == 8:
            self._cleanup()
            self.install_handler(self.id)

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)

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
