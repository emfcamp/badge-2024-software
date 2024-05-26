from typing import Any, Callable

import app
import display
import wifi
from app_components import Menu, clear_background
from events.input import BUTTON_TYPES, Buttons
from urequests import get

APP_STORE_LISTING_URL = "https://apps.badge.emfcamp.org/demo_api/apps.json"

CODE_INSTALL = "CodeInstall"
AVAILABLE = "Available"
INSTALLED = "Installed"
UPDATE = "Update"
REFRESH = "Refresh Apps"


def install_app(app):
    print(f"Installing {app['name']}")


class AppStoreApp(app.App):
    state = "checking_wifi"

    def __init__(self):
        super().__init__()
        self.menu = Menu(
            self,
            menu_items=[
                CODE_INSTALL,
                # AVAILABLE,
                # UPDATE,
                # INSTALLED
            ],
            select_handler=self.on_select,
            back_handler=self.on_cancel,
        )
        self.available_menu = None
        self.installed_menu = None
        self.update_menu = None
        self.app_store_index = []
        self.button_states = Buttons(self)
        self.get_index()

    def check_wifi(self):
        return True
        if self.state != "checking_wifi":
            self.update_state("checking_wifi")
        connected = wifi.status()
        print(wifi.get_ip())
        print("Connected" if connected else "Not connected")
        if not connected:
            self.update_state("no_wifi")
        print(wifi.get_sta_status())
        return connected

    def get_index(self):
        self.check_wifi()
        self.update_state("refreshing_index")
        response = get(APP_STORE_LISTING_URL)
        # self.app_store_index = [
        #     {
        #         "name": "Test App",
        #         "path": "firmware_apps.test_app",
        #         "callable": "TestApp",
        #     }
        # ]
        print(response.json()["items"])
        self.app_store_index = response.json()["items"]
        self.available_menu = Menu(
            self,
            menu_items=[app["manifest"]["app"]["name"] for app in self.app_store_index],
            select_handler=lambda _, i: self.install_app(self.app_store_index[i]),
        )
        self.update_state("main_menu")

    def install_app(self, app):
        print(f"Installing {app['name']}")

    def update_state(self, state):
        print(f"State Transition: '{self.state}' -> '{state}'")
        self.state = state

    def handle_code_input(self, app):
        print(f"Installing {app}")
        self.update_state("main_menu")

    def on_select(self, value, idx):
        if value == CODE_INSTALL:
            self.codeinstall = CodeInstall(
                install_handler=lambda id: self.handle_code_input(id),
                buttons=self.button_states,
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

    def on_cancel(self):
        self.minimise()

    def error_screen(self, ctx, message):
        ctx.gray(1).move_to(0, 0).text(message)

    def update(self, delta):
        if self.menu:
            self.menu.update(delta)
        if self.available_menu:
            self.available_menu.update(delta)
        if self.installed_menu:
            self.installed_menu.update(delta)
        if self.update_menu:
            self.update_menu.update(delta)
        if self.codeinstall:
            self.codeinstall.update()
        return super().update(delta)

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
            self.error_screen(ctx, "No Wi-Fi connection")
        elif self.state == "checking_wifi":
            self.error_screen(ctx, "Checking\nWi-Fi connection")
        elif self.state == "refreshing_index":
            self.error_screen(ctx, "Refreshing app store index")
        elif self.state == "code_install_input" and self.codeinstall:
            self.codeinstall.draw(ctx)
        else:
            self.error_screen(ctx, "Unknown error")
        ctx.restore()

        self.draw_overlays(ctx)


class CodeInstall:
    def __init__(self, install_handler: Callable[[str], Any], buttons: Buttons):
        self.install_handler = install_handler
        self.state = "input"
        self.id: str = ""
        self.buttons_state = buttons

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(1, 0, 0)
        display.hexagon(ctx, 0, 0, 80)
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.move_to(0, 0).text(id)
        ctx.restore()

    def update(self):
        if len(self.id) == 8:
            self.install_handler(self.id)
        if self.buttons_state.get(BUTTON_TYPES["UP"]):
            self.id += "0"
        elif self.buttons_state.get(BUTTON_TYPES["RIGHT"]):
            self.id += "1"
        elif self.buttons_state.get(BUTTON_TYPES["CONFIRM"]):
            self.id += "2"
        elif self.buttons_state.get(BUTTON_TYPES["DOWN"]):
            self.id += "3"
        elif self.buttons_state.get(BUTTON_TYPES["LEFT"]):
            self.id += "4"
        elif self.buttons_state.get(BUTTON_TYPES["CANCEl"]):
            self.id += "5"
