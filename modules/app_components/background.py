import settings
from system.backgrounds.emflogo import EmfLogo
from system.backgrounds.wigglinghexagons import WigglingHexagons
from system.eventbus import eventbus
from system.notification.events import ShowNotificationEvent
from app_components import clear_background
from app_components.utils import path_isfile


class _Background:
    def __init__(self):
        self.reload()

    def reload(self):
        self.runner = None
        self.selection = settings.get("background", ("None", None))
        print(self.selection)
        if self.selection[0] == "hexagons":
            self.runner = WigglingHexagons()
        elif self.selection[0] == "emf logo":
            self.runner = EmfLogo()
        elif self.selection[0] == "None":
            pass
        else:
            path = f"/backgrounds/{self.selection[1]}/app.py"
            print(path)
            if path_isfile(path):
                try:
                    fn = "__Background__"
                    module = __import__(
                        f"backgrounds.{self.selection[1]}.app", None, None, (fn,)
                    )
                    self.runner = getattr(module, fn)()
                except Exception as e:
                    print(f"Error creating background: {e}")
                    eventbus.emit(
                        ShowNotificationEvent(
                            message=f"Background {self.selection[0]} has crashed"
                        )
                    )
                    self.runner = None
            else:
                print("path not a file: " + path)

    def update(self, delta):
        if self.runner:
            self.runner.update(delta)

    def draw(self, ctx):
        if self.runner:
            ctx.save()
            try:
                self.runner.draw(ctx)
            except Exception as e:
                print(f"Error creating background: {e}")
                eventbus.emit(
                    ShowNotificationEvent(
                        message=f"Background {self.selection[0]} has crashed"
                    )
                )
                self.runner = None
            ctx.restore()
        else:
            clear_background(ctx)


Background = _Background()
