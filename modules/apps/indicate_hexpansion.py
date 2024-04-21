import asyncio
from perf_timer import PerfTimer
from tildagonos import EPIN_ND_A, EPIN_ND_B, EPIN_ND_C, EPIN_ND_D, EPIN_ND_E, EPIN_ND_F
from tildagonos import EPIN_BTN_1, EPIN_BTN_2, EPIN_BTN_3, EPIN_BTN_4, EPIN_BTN_5, EPIN_BTN_6
from tildagonos import led_colours
from eventbus import eventbus
from machine import I2C
from eeprom_i2c import EEPROM, T24C256
import vfs

class HexpansionInsertionEvent:
    def __init__(self, port):
        self.port = port

    def __str__(self):
        return f"Hexpansion inserted in port: {self.port}"

class HexpansionRemovalEvent:
    def __init__(self, port):
        self.port = port

    def __str__(self):
        return f"Hexpansion removed from port: {self.port}"

class HexpansionInsertionApp:
    def __init__(self, tildagonos):
        self.tildagonos = tildagonos
        eventbus.on_async(HexpansionInsertionEvent, self.handle_hexpansion_insertion, self)
        eventbus.on_async(HexpansionRemovalEvent, self.handle_hexpansion_removal, self)
        self.mountpoints = {}

    def update(self, delta):
        pass

    def draw(self, display):
        pass

    def _mount_eeprom(self, eep, port):
        mountpoint = f"/hexpansion_{port}"

        first_mount_failed = False
        try:
            print(f"Attempting to mount i2c eeprom from hexpansion port {port}")
            vfs.mount(eep, mountpoint)
        except Exception as e:
            first_mount_failed = True
            print(f"Failed to mount: {e}")
            print("Attempting reformat...")
            vfs.VfsLfs2.mkfs(eep)

        if first_mount_failed:
            try:
                print(f"Attempting to mount i2c eeprom from hexpansion port {port}")
                vfs.mount(eep, mountpoint)
            except Exception:
                print("Mount failed after reformatting, giving up :(")
                return

        self.mountpoints[port] = mountpoint
        print(f"Mounted eeprom to {mountpoint}")

    async def handle_hexpansion_insertion(self, event):
        print(event)

        try:
            # TODO: Automatically determine eeprom size
            eep = EEPROM(I2C(event.port), T24C256)
        except RuntimeError:
            print("No eeprom found")
            eep = None

        if eep is not None:
            self._mount_eeprom(eep, event.port)

    async def handle_hexpansion_removal(self, event):
        print(event)
        if event.port in self.mountpoints:
            print(f"Unmounting {self.mountpoints[event.port]}")
            vfs.umount(self.mountpoints[event.port])

    async def background_update(self):
        self.tildagonos.set_led_power(True)

        hexpansion_plugin_states = [False] * 6
        button_states = [False] * 6

        while True:
            with PerfTimer("indicate hexpansion insertion"):
                self.tildagonos.read_egpios()
                self.tildagonos.leds.fill((0, 0, 0))

                for i, n in enumerate([EPIN_ND_A, EPIN_ND_B, EPIN_ND_C, EPIN_ND_D, EPIN_ND_E, EPIN_ND_F]):
                    hexpansion_present = not self.tildagonos.check_egpio_state(n, readgpios=False)
                    if hexpansion_present:
                        self.tildagonos.leds[13 + i] = led_colours[i]
                    if hexpansion_present and not hexpansion_plugin_states[i]:
                        hexpansion_plugin_states[i] = True
                        eventbus.emit(HexpansionInsertionEvent(port=i + 1))
                    if not hexpansion_present and hexpansion_plugin_states[i]:
                        hexpansion_plugin_states[i] = False
                        eventbus.emit(HexpansionRemovalEvent(port=i + 1))

                for i, n in enumerate([EPIN_BTN_1, EPIN_BTN_2, EPIN_BTN_3, EPIN_BTN_4, EPIN_BTN_5, EPIN_BTN_6]):
                    button_down = not self.tildagonos.check_egpio_state(n, readgpios=False)
                    if button_down:
                        if i:
                            self.tildagonos.leds[i * 2] = led_colours[i]
                        else:
                            self.tildagonos.leds[12] = led_colours[i]
                        self.tildagonos.leds[1 + i * 2] = led_colours[i]
                    if button_down and not button_states[i]:
                        button_states[i] = True
                        eventbus.emit(ButtonDownEvent(button=i))
                    if not button_down and button_states[i]:
                        button_states[i] = False
                        eventbus.emit(ButtonUpEvent(button=i))

                self.tildagonos.leds.write()
            await asyncio.sleep(0.1)


