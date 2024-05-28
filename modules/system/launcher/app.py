import json
import os

from app import App
from app_components import clear_background
from app_components.menu import Menu
from perf_timer import PerfTimer
from system.eventbus import eventbus
from system.scheduler.events import RequestForegroundPushEvent, RequestStartAppEvent


def path_isfile(path):
    # Wow totally an elegant way to do os.path.isfile...
    try:
        return (os.stat(path)[0] & 0x8000) != 0
    except OSError:
        return False


def path_isdir(path):
    try:
        return (os.stat(path)[0] & 0x4000) != 0
    except OSError:
        return False


def recursive_delete(path):
    contents = os.listdir(path)
    for name in contents:
        entry_path = f"{path}/{name}"
        if path_isdir(entry_path):
            recursive_delete(entry_path)
        else:
            os.remove(entry_path)
    os.rmdir(path)


def loadInfo(folder, name):
    try:
        info_file = "{}/{}/__internal__metadata.json".format(folder, name)
        with open(info_file) as f:
            information = f.read()
        return json.loads(information)
    except BaseException:
        return {}


def list_user_apps():
    with PerfTimer("List user apps"):
        apps = []
        app_dir = "/apps"
        try:
            contents = os.listdir(app_dir)
        except OSError:
            # No apps dir full stop
            return []

        for name in contents:
            if not path_isfile(f"{app_dir}/{name}/app.py"):
                continue
            app = {
                "path": name,
                "callable": "main",
                "name": name,
                "icon": None,
                "category": "unknown",
                "hidden": False,
            }
            metadata = loadInfo(app_dir, name)
            app.update(metadata)
            if not app["hidden"]:
                apps.append(app)
        return apps


class Launcher(App):
    def list_core_apps(self):
        core_app_info = [
            ("App store", "firmware_apps.app_store", "AppStoreApp"),
            # ("Name Badge", "hello", "Hello"),
            ("Logo", "firmware_apps.intro_app", "IntroApp"),
            ("Menu demo", "firmware_apps.menu_demo", "MenuDemo"),
            ("Kbd demo", "firmware_apps.text_demo", "TextDemo"),
            # ("Update Firmware", "otaupdate", "OtaUpdate"),
            # ("Wi-Fi Connect", "wifi_client", "WifiClient"),
            # ("Sponsors", "sponsors", "Sponsors"),
            # ("Battery", "battery", "Battery"),
            # ("Accelerometer", "accel_app", "Accel"),
            # ("Magnetometer", "magnet_app", "Magnetometer"),
            ("Update", "system.ota.ota", "OtaUpdate"),
            ("Power Off", "firmware_apps.poweroff", "PowerOff"),
            # ("Settings", "settings_app", "SettingsApp"),
        ]
        core_apps = []
        for core_app in core_app_info:
            core_apps.append(
                {
                    "path": core_app[1],
                    "callable": core_app[2],
                    "name": core_app[0],
                    "icon": None,
                    "category": "unknown",
                }
            )
        return core_apps

    def update_menu(self):
        self.menu_items = self.list_core_apps() + list_user_apps()
        self.menu = Menu(
            self,
            [app["name"] for app in self.menu_items],
            select_handler=self.select_handler,
            back_handler=self.back_handler,
        )

    def launch(self, item):
        module_name = item["path"]
        fn = item["callable"]
        app_id = f"{module_name}.{fn}"
        app = self._apps.get(app_id)
        print(self._apps)
        if app is None:
            print(f"Creating app {app_id}...")
            module = __import__(module_name, None, None, (fn,))
            app = getattr(module, fn)()
            self._apps[app_id] = app
            eventbus.emit(RequestStartAppEvent(app, foreground=True))
        else:
            eventbus.emit(RequestForegroundPushEvent(app))
        # with open("/lastapplaunch.txt", "w") as f:
        #    f.write(str(self.window.focus_idx()))
        # eventbus.emit(RequestForegroundPopEvent(self))

    def __init__(self):
        self.update_menu()
        self._apps = {}

    def select_handler(self, item, idx):
        for app in self.menu_items:
            if item == app["name"]:
                self.launch(app)
                break

    def back_handler(self):
        self.update_menu()
        return
        # if self.current_menu == "main":
        #    return
        # self.set_menu("main")

    def draw(self, ctx):
        clear_background(ctx)
        self.menu.draw(ctx)

    def update(self, delta):
        self.menu.update(delta)
