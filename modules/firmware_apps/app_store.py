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
)
from system.notification.events import ShowNotificationEvent
from app_components.background import Background as bg
from firmware_apps.settings_app import BG_DIR, PAT_DIR
from random import random, choice, randint
from app_components.tokens import symbols


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


APP_STORE_LISTING_URL = "https://apps.badge.emfcamp.org/v1/apps"

CODE_INSTALL = "Use Code"
AVAILABLE = "Browse Apps"
INSTALLED = "Uninstall"
UPDATE = "Update Apps"
REFRESH = "Refresh Apps"


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
        self.codeinstall = None
        self.app_details = None
        self.details_app = None
        self.available_menu_position = 0
        self.response = None
        self.app_store_index = []
        self.apps_with_updates = []
        self.apps_available_dict = {}
        self.app_categories = []
        self.category_filter = None
        self.to_install_app = None
        self.tarball = None
        self.wait_one_cycle = False

    def cleanup_ui_widgets(self):
        widgets = [
            self.menu,
            self.available_categories_menu,
            self.available_menu,
            self.installed_menu,
            self.update_menu,
            self.codeinstall,
            self.app_details,
        ]

        for widget in widgets:
            if widget:
                widget._cleanup()

            self.menu = None
            self.available_categories_menu = None
            self.available_menu = None
            self.installed_menu = None
            self.update_menu = None
            self.codeinstall = None
            self.app_details = None

    def get_index(self):
        if not wifi.status():
            self.update_state("no_wifi")
            return
        self.update_state("refreshing_index")

    def handle_index(self):
        if not self.response:
            print(self.response)
            self.update_state("no_index")
            return
        try:
            self.app_store_index = self.response.json()["items"]
        except Exception:
            print(self.response)
            self.update_state("no_index")
            return

        # build list of categories from index
        self.app_categories = []

        for item in self.app_store_index:
            app_name = item.get("manifest", {}).get("app", {}).get("name", "<unknown>")
            app_category = get_first_category(item["manifest"]["app"])
            if app_category is None:
                print(f"[AppStore] WARNING: app '{app_name}' has no category field!")
                continue
            if app_category not in self.app_categories:
                self.app_categories.append(app_category)

        self.update_state("main_menu")

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
        print(f"Installing {code}")
        try:
            app = [app for app in self.app_store_index if app["code"] == code][0]
            self.to_install_app = app
            self.update_state("installing_app")
        except IndexError:
            # TODO notify user of invalid code
            self.update_state("main_menu")

    def prepare_available_categories_menu(self):
        def on_select(_, i):
            self.category_filter = self.app_categories[i]
            self.available_menu_position = 0
            self.update_state("available_menu")
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

    def prepare_available_menu(self):
        def filtered_index():
            return [
                app
                for app in self.app_store_index
                if get_first_category(app["manifest"]["app"]) == self.category_filter
            ]

        def on_select(_, i):
            self.details_app = filtered_index()[i]
            self.available_menu_position = i
            self.cleanup_ui_widgets()
            self.update_state("app_details")

        def exit_available_menu():
            self.available_menu_position = 0
            self.cleanup_ui_widgets()
            self.update_state("available_categories_menu")

        self.available_menu = Menu(
            self,
            menu_items=[app["manifest"]["app"]["name"] for app in filtered_index()],
            position=self.available_menu_position,
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
            elif value == INSTALLED:
                self.update_state("installed_menu")
            elif value == UPDATE:
                self.update_state("update_menu")
            elif value == REFRESH:
                self.get_index()

        menu_items = [AVAILABLE, CODE_INSTALL, UPDATE]
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
            self.update_state("main_menu")

        def on_select(_, i):
            app_name = self.apps_with_updates[i]["folder"]
            self.to_install_app = self.apps_available_dict[app_name]
            self.update_state("installing_app")
            self.cleanup_ui_widgets()

        def compare_version(v1, v2):
            # compare format v0.0.0
            return v1.split(".") > v2.split(".")

        installed_apps = list_all_apps()
        self.apps_available_dict = {}
        for a in self.app_store_index:
            folder_name = a["id"]["owner"] + "_" + a["id"]["title"]
            folder_name = folder_name.replace("-", "_")
            self.apps_available_dict[folder_name] = a
        self.apps_with_updates = []
        for ia in installed_apps:
            if ia["folder"] in self.apps_available_dict:
                app_dict = self.apps_available_dict[ia["folder"]]
                latest_version = app_dict["manifest"]["metadata"]["version"]
                print("App: " + ia["name"])
                print(f"Latest version: {latest_version}")
                print("Installed version: " + ia["version"])

                if compare_version(latest_version, ia["version"]):
                    self.apps_with_updates.append(ia)
            else:
                print("No app in app store matching: ", ia)
        if len(self.apps_with_updates):
            self.update_menu = Menu(
                self,
                menu_items=[app["name"] for app in self.apps_with_updates],
                select_handler=on_select,
                back_handler=on_cancel,
                focused_item_font_size=fourteen_pt,
                item_font_size=ten_pt,
            )
        else:
            self.update_state("main_menu")
            eventbus.emit(ShowNotificationEvent("All apps up to date!"))

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
            if not wifi.status():
                self.update_state("wifi_init")
                return
            print("calling get index")
            self.get_index()
        elif self.state == "wifi_init":
            try:
                wifi.connect()
            except Exception:
                pass
            self.update_state("wifi_connecting")
        elif self.state == "wifi_connecting":
            if wifi.status():
                self.update_state("init")
        elif self.state == "index_received":
            self.handle_index()
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
        elif self.state == "installed_menu" and not self.installed_menu:
            self.prepare_installed_menu()
        elif self.state == "update_menu" and not self.update_menu:
            self.prepare_update_menu()
        elif self.state == "refreshing_index":
            try:
                self.response = await async_helpers.unblock(
                    get, render_update, APP_STORE_LISTING_URL
                )
            except Exception:
                self.update_state("no_index")
            else:
                self.update_state("index_received")
        elif self.state == "installing_app":
            # We wait one cycle after background_update is called to ensure the
            # installation screen is drawn
            await async_helpers.unblock(
                self.install_app, render_update, self.to_install_app
            )
            self.to_install_app = None
        if self.menu:
            self.menu.update(delta)
        if self.available_categories_menu:
            self.available_categories_menu.update(delta)
        if self.available_menu:
            self.available_menu.update(delta)
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
        elif self.state == "available_menu" and self.available_menu:
            self.available_menu.draw(ctx)
        elif self.state == "available_menu" and not self.available_menu:
            pass
        elif self.state == "app_details" and self.app_details:
            self.app_details.draw(ctx)
        elif self.state == "app_details" and not self.app_details:
            pass
        elif self.state == "installed_menu" and self.installed_menu:
            self.installed_menu.draw(ctx)
        elif self.state == "update_menu" and self.update_menu:
            self.update_menu.draw(ctx)
        elif self.state == "no_wifi":
            self.error_screen(ctx, "No Wi-Fi\nconnection")
        elif self.state == "no_wifi":
            self.error_screen(ctx, "Couldn't\nconnect to\napp store")
        elif self.state == "checking_wifi":
            self.error_screen(ctx, "Checking\nWi-Fi connection")
        elif self.state in ("wifi_init", "wifi_connecting"):
            self.error_screen(ctx, "Connecting\nWi-Fi...\n")
        elif self.state == "refreshing_index":
            self.error_screen(ctx, "Refreshing\napp store\nindex")
        elif self.state == "index_received":
            self.error_screen(ctx, "App store\nindex\nreceived")
        elif self.state == "no_index":
            self.error_screen(ctx, "Index\nerror")
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
            print("Unkown error " + self.state)
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
        # tarballGenerator = self.download_file(app["tarballUrl"])

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
