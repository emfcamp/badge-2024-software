import gc
import gzip
import io
import os
from tarfile import DIRTYPE, TarFile
from typing import Any, Callable

import app
import wifi
from app_components import Menu, clear_background, fourteen_pt, sixteen_pt, ten_pt
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from system.launcher.app import APP_DIR
from urequests import get

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

    def connect_wifi(self):
        ssid = wifi.get_ssid()
        if not ssid:
            print("No WIFI config!")
            return

        if not wifi.status():
            wifi.connect()
            while True:
                print("Connecting to")
                print(f"{ssid}...")
                if wifi.wait():
                    # Returning true means connected
                    break

    def check_wifi(self):
        print("in check_wifi")
        self.update_state("checking_wifi")
        self.connect_wifi()
        # return True

        if self.state != "checking_wifi":
            self.update_state("checking_wifi")
        connected = wifi.status()
        # print(wifi.get_ip())
        print("Connected" if connected else "Not connected")
        if not connected:
            self.update_state("no_wifi")
        # print(wifi.get_sta_status())
        return connected

    def get_index(self):
        if not self.check_wifi():
            self.update_state("no_wifi")
        self.update_state("refreshing_index")

    def background_update(self, delta):
        if self.state == "refreshing_index":
            self.response = get(APP_STORE_LISTING_URL)
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
            ## This is fine to block because we only call it from background_update
            gc.collect()

            tarball = get(app["tarballUrl"])
            # tarballGenerator = self.download_file(app["tarballUrl"])

            # TODO: Investigate using deflate.DeflateIO instead. Can't do it now
            # because it's not available in the simulator.
            tar = gzip.decompress(tarball.content)
            gc.collect()
            t = TarFile(fileobj=io.BytesIO(tar))

            validate_app_files(t)

            # TODO: Check we have enough storage in advance

            for i in t:
                if i:
                    if i.type == DIRTYPE:
                        dirname = os.path.join(APP_DIR, i.name)
                        if not os.path.exists(dirname):
                            os.makedirs(dirname)
                    else:
                        filename = os.path.join(APP_DIR, i.name)
                        f = t.extractfile(i)
                        if f:
                            with open(filename, "wb") as file:
                                while data := f.read():
                                    file.write(data)

            # TODO: Success/Failure Notification
            self.update_state("main_menu")
        except MemoryError:
            gc.collect()
            self.update_state("install_oom")
        except Exception as e:
            print(e)

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

    def on_select(self, value, idx):
        if value == CODE_INSTALL:
            self.codeinstall = CodeInstall(
                install_handler=lambda id: self.handle_code_input(id), app=self
            )
            if self.menu:
                self.menu._cleanup()
                self.menu = None
            self.update_state("code_install_input")
        elif value == AVAILABLE:
            self.update_state("available_menu")
        elif value == INSTALLED:
            self.update_state("installed_menu")
        elif value == UPDATE:
            self.update_state("update_menu")
        elif value == REFRESH:
            self.get_index()

    def on_cancel(self):
        self.minimise()

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
            print("calling get index")
            self.get_index()
        elif self.state == "index_received":
            self.handle_index()
        elif self.state == "main_menu" and not self.menu:
            self.menu = Menu(
                self,
                menu_items=[
                    CODE_INSTALL,
                    AVAILABLE,
                    # UPDATE,
                    # INSTALLED
                ],
                select_handler=self.on_select,
                back_handler=self.on_cancel,
            )
        elif self.state == "available_menu" and not self.available_menu:

            def wouldveUsedALambdaButICant(_, i):
                self.to_install_app = self.app_store_index[i]
                self.update_state("installing_app")

            def exit_available_menu():
                if self.available_menu:
                    self.available_menu._cleanup()
                    self.available_menu = None
                self.update_state("main_menu")

            self.available_menu = Menu(
                self,
                menu_items=[
                    app["manifest"]["app"]["name"] for app in self.app_store_index
                ],
                select_handler=wouldveUsedALambdaButICant,
                back_handler=exit_available_menu,
                focused_item_font_size=fourteen_pt,
                item_font_size=ten_pt,
            )

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
        elif self.state == "checking_wifi":
            self.error_screen(ctx, "Checking\nWi-Fi connection")
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
            eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
            print("calling install handler")
            self.install_handler(self.id)

    def draw(self, ctx):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.font_size = ten_pt
        ctx.gray(1).move_to(0, -3 * ten_pt).text("Enter code:")
        ctx.font_size = sixteen_pt
        ctx.gray(1).move_to(0, 0).text(self.id)
        ctx.restore()


def validate_app_files(tar):
    prefix = None
    seen_app_py = False
    for i, f in enumerate(tar):
        print(f.name)
        if i == 0 and f.isdir():
            prefix = f.name
            continue
        if prefix and not f.name.startswith(prefix):
            raise ValueError(f"Invalid file {f.name}")
        if not seen_app_py and prefix and f.name == prefix + "/app.py":
            seen_app_py = True
    if not prefix:
        raise ValueError("No root dir in tarball")
    if not seen_app_py:
        raise ValueError("No app.py found in tarball")
