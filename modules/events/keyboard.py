from .input import Button, BUTTON_TYPES

letters = {
    letter: Button(letter, "Keyboard") for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
}

numbers = {number: Button(number, "Keyboard") for number in "0123456789"}

symbols = {
    symbol: Button(symbol, "Keyboard")
    for symbol in """!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~"""
}

modifiers = {
    "SPACE": Button("SPACE", "Keyboard"),
    "SHIFT": Button("SHIFT", "Keyboard"),
    "CTRL": Button("CTRL", "Keyboard"),
    "ALT": Button("ALT", "Keyboard"),
    "ESCAPE": Button("ESCAPE", "Keyboard", BUTTON_TYPES["CANCEL"]),
    "DELETE": Button("DELETE", "Keyboard"),
    "ENTER": Button("ENTER", "Keyboard", BUTTON_TYPES["CONFIRM"]),
    "UP": Button("UP", "Keyboard", BUTTON_TYPES["UP"]),
    "DOWN": Button("DOWN", "Keyboard", BUTTON_TYPES["DOWN"]),
    "LEFT": Button("LEFT", "Keyboard", BUTTON_TYPES["LEFT"]),
    "RIGHT": Button("RIGHT", "Keyboard", BUTTON_TYPES["RIGHT"]),
}

KEYBOARD_BUTTONS = letters | numbers | symbols | modifiers
