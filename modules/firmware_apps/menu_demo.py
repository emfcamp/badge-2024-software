from typing import Literal

from app import App
from app_components import Menu, Notification, clear_background

main_menu_items = ["numbers", "letters", "words"]

numbers_menu_items = ["one", "two", "three", "four", "five"]

letters_menu_items = ["a", "b", "c", "d", "e"]

words_menu_items = ["emfcamp", "bodgeham-on-wye", "hackers", "hexpansions", "tildagon"]


class MenuDemo(App):
    def __init__(self):
        super().__init__()
        self.current_menu = "main"
        self.menu = Menu(
            self,
            main_menu_items,
            select_handler=self.select_handler,
            back_handler=self.back_handler,
        )
        self.notification = None

    def select_handler(self, item, idx):
        if item in ["numbers", "letters", "words", "main"]:
            self.set_menu(item)
        else:
            self.notification = Notification('You selected "' + item + '"!')

    def set_menu(self, menu_name: Literal["main", "numbers", "letters", "words"]):
        self.menu._cleanup()
        self.current_menu = menu_name
        if menu_name == "main":
            self.menu = Menu(
                self,
                main_menu_items,
                select_handler=self.select_handler,
                back_handler=self.back_handler,
            )
        elif menu_name == "numbers":
            self.menu = Menu(
                self,
                numbers_menu_items,
                select_handler=self.select_handler,
                back_handler=self.back_handler,
            )
        elif menu_name == "letters":
            self.menu = Menu(
                self,
                letters_menu_items,
                select_handler=self.select_handler,
                back_handler=self.back_handler,
            )
        elif menu_name == "words":
            self.menu = Menu(
                self,
                words_menu_items,
                select_handler=self.select_handler,
                back_handler=self.back_handler,
            )

    def back_handler(self):
        if self.current_menu == "main":
            self.minimise()
        self.set_menu("main")

    def draw(self, ctx):
        clear_background(ctx)
        self.menu.draw(ctx)
        if self.notification:
            self.notification.draw(ctx)

    def update(self, delta):
        self.menu.update(delta)
        if self.notification:
            self.notification.update(delta)
