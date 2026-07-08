import json
import os
import sys

from app import App
from app_components import clear_background
from app_components.menu import Menu
from perf_timer import PerfTimer
from system.eventbus import eventbus
from events import Event
from events.emote import EmoteNegativeEvent
from system.scheduler.events import (
    RequestForegroundPushEvent,
    RequestStartAppEvent,
    RequestStopAppEvent,
)
from system.notification.events import ShowNotificationEvent
from app_components.background import Background as bg
from app_components.tokens import symbols

APP_DIR = ["/apps"]
APP_INSTALL_DIR = "/apps"


class InstallNotificationEvent(Event):
    pass


class AppDirAddedNotificationEvent(Event):
    def __init__(self, path):
        self.path = path


class AppDirRemovedNotificationEvent(Event):
    def __init__(self, path):
        self.path = path


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


def load_info(folder, name):
    try:
        info_file = "{}/{}/metadata.json".format(folder, name)
        with open(info_file) as f:
            information = f.read()
        return json.loads(information)
    except BaseException:
        return {}


def list_user_apps():
    with PerfTimer("List user apps"):
        apps = []
        contents = []
        for d in APP_DIR:
            try:
                contents.extend([(d, x) for x in os.listdir(d)])
            except (OSError, UnicodeError):
                # directory or mount point don't exist
                pass

        for dirname, name in contents:
            path = dirname
            for p in sys.path:
                if p and dirname.startswith(p):
                    path = dirname[len(p) :]
                    break
            path = ".".join(path.lstrip("/").split("/"))
            app = {
                "path": f"{path}.{name}.app",
                "callable": "__app_export__",
                "name": name,
                "folder": name,
                "hidden": False,
            }
            metadata = load_info(dirname, name)
            if "version" not in metadata:
                app["version"] = "0.0.0"
            app.update(metadata)
            if not app["hidden"]:
                apps.append(app)
        return apps


class Launcher(App):
    def __init__(self):
        self.menu = None
        self.update_menu()
        self._apps = {}
        eventbus.on_async(RequestStopAppEvent, self._handle_stop_app, self)
        eventbus.on_async(
            InstallNotificationEvent, self._handle_refresh_notifications, self
        )
        eventbus.on_async(
            AppDirAddedNotificationEvent, self._handle_dir_added_notification, self
        )
        eventbus.on_async(
            AppDirRemovedNotificationEvent, self._handle_dir_removed_notification, self
        )

    async def _handle_refresh_notifications(self, _):
        self.update_menu()

    async def _handle_dir_added_notification(self, event):
        APP_DIR.append(event.path)
        self.update_menu()

    async def _handle_dir_removed_notification(self, event):
        try:
            APP_DIR.remove(event.path)
        except ValueError:
            pass
        self.update_menu()

    async def _handle_stop_app(self, event: RequestStopAppEvent):
        # If an app is stopped, remove our cache of it as it needs restarting
        for key, app in self._apps.items():
            if app == event.app:
                self._apps[key] = None
                print(f"Removing launcher cache for {key}")

    def list_core_apps(self):
        core_app_info = [
            ("App store", "firmware_apps.app_store", "AppStoreApp"),
            ("Sponsors", "firmware_apps.sponsors", "Sponsors"),
            # ("Name Badge", "hello", "Hello"),
            # ("Logo", "firmware_apps.intro_app", "IntroApp"),
            # ("Menu demo", "firmware_apps.menu_demo", "MenuDemo"),
            # ("Kbd demo", "firmware_apps.text_demo", "TextDemo"),
            # ("Update Firmware", "otaupdate", "OtaUpdate"),
            # ("Inhibit LEDs", "firmware_apps.patterninhibit", "PatternInhibit"),
            # ("Wi-Fi Connect", "wifi_client", "WifiClient"),
            # ("Sponsors", "sponsors", "Sponsors"),
            # ("Battery", "battery", "Battery"),
            # ("Accelerometer", "accel_app", "Accel"),
            # ("Magnetometer", "magnet_app", "Magnetometer"),
            ("Update", "system.ota.ota", "OtaUpdate"),
            ("Hexpansions", "firmware_apps.hexpansionfw", "HexpansionInfoApp"),
            ("Power Off", "firmware_apps.poweroff", "PowerOff"),
            ("Settings", "firmware_apps.settings_app", "SettingsApp"),
            # ("Settings", "settings_app", "SettingsApp"),
            # ("ESPNow ping", "firmware_apps.espnow_ping", "ESPNowPing"),
        ]
        core_apps = []
        for core_app in core_app_info:
            core_apps.append(
                {
                    "path": core_app[1],
                    "callable": core_app[2],
                    "name": core_app[0],
                }
            )
        return core_apps

    def update_menu(self):
        self.menu_items = self.list_core_apps() + list_user_apps()
        if self.menu:
            self.menu._cleanup()
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
            try:
                module = __import__(module_name, None, None, (fn,))
                app = getattr(module, fn)()
            except Exception as e:
                print(f"Error creating app: {e}")
                sys.print_exception(e, sys.stderr)
                eventbus.emit(
                    ShowNotificationEvent(message=f"{item['name']} has crashed")
                )
                eventbus.emit(EmoteNegativeEvent())
                return
            self._apps[app_id] = app
            eventbus.emit(RequestStartAppEvent(app, foreground=True))
        else:
            eventbus.emit(RequestForegroundPushEvent(app))
        # with open("/lastapplaunch.txt", "w") as f:
        #    f.write(str(self.window.focus_idx()))
        # eventbus.emit(RequestForegroundPopEvent(self))

    def select_handler(self, item, idx):
        for app in self.menu_items:
            if item == app["name"]:
                self.launch(app)
                break

    def back_handler(self):
        self.menu._cleanup()
        self.update_menu()
        return
        # if self.current_menu == "main":
        #    return
        # self.set_menu("main")

    def draw(self, ctx):
        clear_background(ctx)
        bg.draw(ctx)
        self.menu.draw(ctx)

    def update(self, delta):
        bg.update(delta)
        self.menu.update(delta)

    async def background_task(self):
        # oneshot at startup, not a loop like most apps backgroud_tasks

        try:
            with open("/autoexec.bat", "r") as f:
                lines = f.readlines()
                if len(lines) == 0:
                    raise RuntimeError("autoexec.bat must name an app to launch")
                app_subname = lines[0].strip()
                found = False
                for app in self.menu_items:
                    if app["name"].find(app_subname) != -1:
                        self.launch(app)
                        found = True
                        break
                if not found:
                    raise RuntimeError(f"No app named '{app_subname}'")

        except Exception as e:
            # don't log file-not-found as an error because that's the default
            # for all badges.
            if isinstance(e, OSError) and e.errno == 2:
                pass
            else:
                # log exceptions but don't propagate - an autoexec failure
                # shouldn't crash the launcher. Most badges will emit this message
                # at startup.
                print(f"autoexec.bat not processed fully: {type(e)} {e}")
                eventbus.emit(
                    ShowNotificationEvent(
                        message=f"autoexec {symbols['bat_open']} failed. {e}"
                    )
                )
