from typing import Any, Callable

import app
import display
import wifi
from app_components import Menu, clear_background
from urequests import get

APP_STORE_LISTING_URL = "https://apps.badge.emfcamp.org/demo_api/apps.json"

BOOP_INSTALL = "BoopInstall"
AVAILABLE = "Available"
INSTALLED = "Installed"
UPDATE = "Update"
REFRESH = "Refresh Apps"


class AppStoreApp(app.App):
    state = "checking_wifi"

    def __init__(self):
        super().__init__()
        self.menu = Menu(
            self,
            menu_items=[BOOP_INSTALL, AVAILABLE, UPDATE, INSTALLED],
            select_handler=self.on_select,
            back_handler=self.on_cancel,
        )
        self.available_menu = None
        self.installed_menu = None
        self.update_menu = None
        self.app_store_index = []
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
        print(response.json().items)
        self.available_menu = Menu(
            self,
            menu_items=[app["manifest"]["app"]["name"] for app in self.app_store_index],
        )
        self.update_state("main_menu")

    def update_state(self, state):
        print(f"State Transition: '{self.state}' -> '{state}'")
        self.state = state

    def on_select(self, value):
        if value == BOOP_INSTALL:
            self.boopinstall = BoopInstall(
                install_handler=lambda id: print(f"Installing {id}")
            )
            self.update_state("boop_install")
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
        else:
            self.error_screen(ctx, "Unknown error")
        ctx.restore()

        self.draw_overlays(ctx)


class BoopInstall:
    def __init__(self, install_handler: Callable[[str], Any]):
        self.install_handler = install_handler
        self.state = "input"
        self.id: str = ""

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(1, 0, 0)
        display.hexagon(ctx, 0, 0, 80)
        ctx.restore()
