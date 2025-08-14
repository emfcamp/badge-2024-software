from app import App
from app_components import Menu, clear_background

main_menu_items = [
    "AND Digital",
    "Mathworks",
    "Allnet China",
    "Bosch",
    "Espressif",
    "Texas Instruments",
]


class Sponsors(App):
    def __init__(self):
        super().__init__()
        self.current_menu = "main"
        self.menu = Menu(
            self,
            main_menu_items,
            select_handler=print,
            back_handler=self.back_handler,
        )
        self.notification = None

    def back_handler(self):
        self.minimise()

    def draw(self, ctx):
        clear_background(ctx)
        self.menu.draw(ctx)
        if self.notification:
            self.notification.draw(ctx)

    def update(self, delta):
        self.menu.update(delta)
        if self.notification:
            self.notification.update(delta)
