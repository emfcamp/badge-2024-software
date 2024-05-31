import gc
import gzip
import io
import json
import os
import tarfile
from tarfile import DIRTYPE, TarFile
from typing import Any, Callable

import app
import wifi
from app_components import Menu, clear_background, fourteen_pt, sixteen_pt, ten_pt
from events.input import BUTTON_TYPES, ButtonDownEvent
from requests import get
from system.eventbus import eventbus
from system.launcher.app import APP_DIR, list_user_apps, InstallNotificationEvent
from system.notification.events import ShowNotificationEvent


def dir_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) != 0
    except OSError:
        return False


def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False


APP_STORE_LISTING_LIVE_URL = "https://api.badge.emf.camp/v1/apps"
APP_STORE_LISTING_URL = "https://apps.badge.emfcamp.org/demo_api/apps.json"

CODE_INSTALL = "CodeInstall"
AVAILABLE = "Available"
INSTALLED = "Installed"
UPDATE = "Update"
REFRESH = "Refresh Apps"


class AppStoreApp(app.App):
    state = "init"

    def __init__(self):
        super().__init__()
        self.menu = None
        self.available_menu = None
        self.installed_menu = None
        self.update_menu = None
        self.codeinstall = None
        self.response = None
        self.app_store_index = []
        self.to_install_app = None
        self.tarball = None

    def cleanup_ui_widgets(self):
        widgets = [
            self.menu,
            self.available_menu,
            self.installed_menu,
            self.update_menu,
            self.codeinstall,
        ]

        for widget in widgets:
            if widget:
                widget._cleanup()
                widget = None

    def get_index(self):
        if not wifi.status():
            self.update_state("no_wifi")
            return
        self.update_state("refreshing_index")

    def background_update(self, delta):
        if self.state == "refreshing_index":
            try:
                self.response = get(APP_STORE_LISTING_LIVE_URL)
            except Exception:
                try:
                    self.response = get(APP_STORE_LISTING_URL)
                except Exception:
                    self.update_state("no_index")
                    return
            self.update_state("index_received")
        if self.to_install_app:
            self.install_app(self.to_install_app)
            self.to_install_app = None

    def handle_index(self):
        if not self.response:
            return
        self.app_store_index = self.response.json()["items"]

        self.update_state("main_menu")

    def install_app(self, app):
        try:
            install_app(app)
            self.update_state("main_menu")
            eventbus.emit(InstallNotificationEvent())
            eventbus.emit(ShowNotificationEvent("Installed the app!"))
        except MemoryError:
            self.update_state("install_oom")
        except Exception as e:
            print(e)
            eventbus.emit(ShowNotificationEvent("Couldn't install app"))
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

    def prepare_available_menu(self):
        def on_select(_, i):
            self.to_install_app = self.app_store_index[i]
            self.update_state("installing_app")
            if self.available_menu:
                self.available_menu._cleanup()

        def exit_available_menu():
            self.cleanup_ui_widgets()
            self.update_state("main_menu")

        self.available_menu = Menu(
            self,
            menu_items=[app["manifest"]["app"]["name"] for app in self.app_store_index],
            select_handler=on_select,
            back_handler=exit_available_menu,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def prepare_main_menu(self):
        def on_cancel():
            self.minimise()

        def on_select(value, idx):
            if value == CODE_INSTALL:
                self.cleanup_ui_widgets()
                self.codeinstall = CodeInstall(
                    install_handler=lambda id: self.handle_code_input(id), app=self
                )
                self.update_state("code_install_input")
            elif value == AVAILABLE:
                self.update_state("available_menu")
            elif value == INSTALLED:
                self.update_state("installed_menu")
            elif value == UPDATE:
                self.update_state("update_menu")
            elif value == REFRESH:
                self.get_index()

        self.menu = Menu(
            self,
            menu_items=[
                CODE_INSTALL,
                AVAILABLE,
                # UPDATE,
                INSTALLED,
            ],
            select_handler=on_select,
            back_handler=on_cancel,
        )

    def prepare_installed_menu(self):
        def on_cancel():
            self.cleanup_ui_widgets()
            self.update_state("main_menu")

        def on_select(_, __):
            # TODO maybe implement uninstalling apps
            pass

        installed_apps = list_user_apps()

        self.installed_menu = Menu(
            self,
            menu_items=[app["name"] for app in installed_apps],
            select_handler=on_select,
            back_handler=on_cancel,
            focused_item_font_size=fourteen_pt,
            item_font_size=ten_pt,
        )

    def error_screen(self, ctx, message):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        lines = message.split("\n")
        start_y = -len(lines) * ctx.font_size / 2

        for i, line in enumerate(lines):
            ctx.gray(1).move_to(0, start_y + i * ctx.font_size).text(line)
        ctx.restore()

    def update(self, delta):
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
        elif self.state == "available_menu" and not self.available_menu:
            self.prepare_available_menu()
        elif self.state == "installed_menu" and not self.installed_menu:
            self.prepare_installed_menu()

        if self.menu:
            self.menu.update(delta)
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
        clear_background(ctx)
        if self.state == "main_menu" and self.menu:
            self.menu.draw(ctx)
        elif self.state == "available_menu" and self.available_menu:
            self.available_menu.draw(ctx)
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
        ctx.restore()

        self.draw_overlays(ctx)


class CodeInstall:
    def __init__(self, install_handler: Callable[[str], Any], app: app.App):
        self.install_handler = install_handler
        self.state = "input"
        self.id: str = ""
        eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["UP"] in event.button:
            self.id += "0"
        elif BUTTON_TYPES["RIGHT"] in event.button:
            self.id += "1"
        elif BUTTON_TYPES["CONFIRM"] in event.button:
            self.id += "2"
        elif BUTTON_TYPES["DOWN"] in event.button:
            self.id += "3"
        elif BUTTON_TYPES["LEFT"] in event.button:
            self.id += "4"
        elif BUTTON_TYPES["CANCEL"] in event.button:
            self.id += "5"

        if len(self.id) == 8:
            self._cleanup()
            self.install_handler(self.id)

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)

    def draw(self, ctx):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.font_size = ten_pt
        ctx.gray(1).move_to(0, -3 * ten_pt).text("Enter code:")
        ctx.font_size = sixteen_pt
        ctx.gray(1).move_to(0, 0).text(self.id)
        ctx.restore()


def install_app(app):
    try:
        ## This is fine to block because we only call it from background_update
        print("GC")
        gc.collect()

        print(f"Getting {app["tarballUrl"]}")
        tarball = get(app["tarballUrl"])
        # tarballGenerator = self.download_file(app["tarballUrl"])

        # TODO: Investigate using deflate.DeflateIO instead. Can't do it now
        # because it's not available in the simulator.
        print("Decompressing")
        tar = gzip.decompress(tarball.content)
        gc.collect()
        tar_bytesio = io.BytesIO(tar)

        print("Validating")
        prefix = find_app_root_dir(TarFile(fileobj=tar_bytesio)).rstrip('/')
        tar_bytesio.seek(0)
        print(f"Found app prefix: {prefix}")
        app_py_info = find_app_py_file(prefix, TarFile(fileobj=tar_bytesio))
        print(f"Found app.py at: {app_py_info.name}")
        tar_bytesio.seek(0)

        # TODO: Check we have enough storage in advance
        # TODO: Does the app already exist? Delete it

        # Make sure apps dir exists
        try:
            os.mkdir(APP_DIR)
        except OSError:
            pass

        app_module_name = '_'.join(prefix.split('-')[0:-1])

        t = TarFile(fileobj=tar_bytesio)
        for i in t:
            if i:
                if not i.name.startswith(prefix):
                    continue
                if i.type == DIRTYPE:
                    dirname = f"{APP_DIR}/{i.name}"
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
                    filename = f"{APP_DIR}/{i.name}"
                    filename = filename.replace(prefix, app_module_name, 1)
                    print(f"Filename: {filename}")
                    f = t.extractfile(i)
                    if f:
                        with open(filename, "wb") as file:
                            while data := f.read():
                                file.write(data)

        internal_manifest = {
            "name": app["manifest"]["app"]["name"],
            "hidden": False,
        }
        json_path = f"{APP_DIR}/{app_module_name}/metadata.json"
        print(f"Json path: {json_path}")
        with open(json_path, "w+") as internal_manifest_file_handler:
            json.dump(internal_manifest, internal_manifest_file_handler)

    except MemoryError as e:
        gc.collect()
        raise e
    except Exception as e:
        print(e)
        raise e


def validate_app_files(tar):
    prefix = find_app_root_dir(tar)
    app_py_path = find_app_py_file(prefix, tar)
    print(f"Found app.py at: {app_py_path}")
    return prefix


def find_app_root_dir(tar):
    print("Finding root dir...")
    root_dir = None
    for i, f in enumerate(tar):
        print(f"prefix: {i}, name: {f.name}")
        slash_count = len(f.name.split("/")) - 1
        if slash_count == 1 and f.isdir():
            if root_dir is None:
                root_dir = f.name
            else:
                raise ValueError("More than one root directory found in app tarball")
    if root_dir is None:
        raise ValueError("No root dir in tarball")
    return root_dir


def find_app_py_file(prefix, tar) -> tarfile.TarInfo:
    print("Finding app.py...")
    found_app_py = False
    expected_path = f"{prefix}/app.py"
    app_py_info = None

    for i, f in enumerate(tar):
        print(f"prefix: {i}, name: {f.name}")
        if f.name == expected_path:
            found_app_py = True
            app_py_info = f
    if not found_app_py:
        raise ValueError(
            f"No app.py found in tarball, expected location: {expected_path}"
        )
    return app_py_info
