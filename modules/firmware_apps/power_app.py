import app
import power

from app_components.menu import Menu
from app_components.background import Background as bg
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from system.patterndisplay.events import (
    PatternDisable,
    PatternEnable,
)

_STORAGE_V = 3.8
_STORAGE_CHARGING_OFFSET_V = 0.07  # battery reads ~0.07V high while actively charging


class PowerApp(app.App):
    def __init__(self):
        super().__init__()
        # state: "menu", "poweroff", "standby", "charging_poweroff",
        #        "storage_settling",
        #        "storage_charging", "storage_discharging", "storage_discharging_settling",
        #        "storage_poweroff"
        self.state = "menu"
        self.screen_blank = False
        self._prev_blank = False
        self._force_render = False
        self._ignore_next_button = False
        self._storage_settle_ms = 0.0  # time spent waiting for voltage to settle
        self._fading_to_off = False  # True while LEDs are fading to 0 before settling
        self._led_b = -1  # last written LED brightness
        self._display_brightness = 0.0
        self.menu = self._build_menu()

    def _build_menu(self):
        return Menu(
            self,
            ["Standby", "Power Off", "Storage"],
            select_handler=self._menu_select,
            back_handler=self._menu_back,
        )

    def _hardware_power(self, on=True):
        from egpio import ePin
        from tildagonos import tildagonos

        HEXPANSION_POWER = {
            (2, 12),
            (2, 13),
            (1, 8),
            (1, 9),
            (1, 10),
            (1, 11),
        }

        for epin in HEXPANSION_POWER:
            pin = ePin(epin, ePin.OUT)
            if on:
                pin.off()
            else:
                pin.on()

        pin = ePin((2, 2), ePin.OUT)
        if on:
            pin.on()
        else:
            pin.off()

        tildagonos.set_led_power(on)

    def _is_done_charging(self):
        return power.BatteryChargeState() in ("Not Charging", "Terminated")

    def _update_discharging_leds(self, target, delta=None):
        """Set LED brightness between 0.0–1.0
        Uses delta to ramp smoothly at 1%/ms - if not specified then LEDs will update instantly.
        """
        from tildagonos import tildagonos

        if delta is None:
            self._display_brightness = target
        else:
            step = 0.01 / 1000.0 * delta  # 1% per 1 s
            self._display_brightness += max(
                -step, min(step, target - self._display_brightness)
            )
        b = int(255 * self._display_brightness)
        if self._led_b != b:
            colour = (b, b, b)
            for i in range(19):
                tildagonos.leds[i] = colour
            tildagonos.set_led_power(b > 0)
            if b == 0:
                self._hardware_power(on=False)  # hexpansion off when fully dark
            tildagonos.leds.write()
            self._led_b = b

    def _get_standby_power_lines(self):
        try:
            battery_pct = power.BatteryLevel()
            charge_current_ma = power.Icharge() * 1000.0
            charge_state = power.BatteryChargeState()
            return (
                f"Battery: {battery_pct:.0f}%",
                f"Charge Current: {charge_current_ma:.0f} mA",
                f"State: {charge_state}",
            )
        except Exception:
            return ("Battery: n/a", "Charge Current: n/a", "State: n/a")

    def _menu_select(self, item, _idx):
        self.menu._cleanup()
        eventbus.emit(PatternDisable())
        if item == "Power Off":
            self._hardware_power(on=False)
            if self._is_done_charging():
                power.Off()
                self.state = "poweroff"
            else:
                self.state = "charging_poweroff"
        elif item == "Storage":
            self._hardware_power(on=False)
            self._storage_settle_ms = 0.0
            self.state = "storage_settling"
        else:
            self._hardware_power(on=False)
            self.state = "standby"
        self._force_render = True
        self._ignore_next_button = True
        eventbus.on_async(ButtonDownEvent, self._handle_buttondown, self)

    def _menu_back(self):
        self.menu._cleanup()
        self.minimise()

    async def _handle_buttondown(self, event: ButtonDownEvent):
        if self._ignore_next_button:
            self._ignore_next_button = False
            return
        if self.state in (
            "standby",
            "charging_poweroff",
            "storage_settling",
            "storage_charging",
            "storage_discharging",
            "storage_discharging_settling",
        ) and (
            BUTTON_TYPES["CANCEL"] in event.button
            or BUTTON_TYPES["LEFT"] in event.button
        ):
            eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
            eventbus.emit(PatternEnable())
            self._hardware_power(on=True)
            self.state = "menu"
            self.screen_blank = False
            self._prev_blank = False
            self.menu = self._build_menu()
            self.terminate()
            return
        name = event.button.name
        if (
            name in ("LEFTPROX", "RIGHTPROX")
            or name.startswith("TOUCH")
            or name.startswith("JOY")
        ):
            return
        self.screen_blank = not self.screen_blank

    def update(self, delta):
        if self.state == "menu":
            self.menu.update(delta)
            return True
        # In poweroff/standby: only render when screen_blank changes
        if self._force_render:
            self._force_render = False
            return True
        if self._prev_blank != self.screen_blank:
            self._prev_blank = self.screen_blank
            return True
        if self.state in ("standby", "charging_poweroff"):
            if self.state == "charging_poweroff" and self._is_done_charging():
                power.Off()
                self.state = "poweroff"
            if not self.screen_blank:
                return True

        elif self.state == "storage_settling":
            self._storage_settle_ms += delta
            if self._storage_settle_ms >= 250:
                vbat = round(power.Vbat(), 2)
                is_charging = power.BatteryChargeState() not in (
                    "Not Charging",
                    "Terminated",
                )
                vbat_adj = (
                    round(vbat - _STORAGE_CHARGING_OFFSET_V, 2) if is_charging else vbat
                )
                if vbat_adj < _STORAGE_V:
                    self.state = "storage_charging"
                elif vbat_adj > _STORAGE_V:
                    self._display_brightness = 0.0
                    self._fading_to_off = False
                    self._led_b = -1
                    self._storage_settle_ms = 0.0
                    self.state = "storage_discharging"
                else:
                    power.Off()
                    self.state = "storage_poweroff"
            if not self.screen_blank:
                return True

        elif self.state == "storage_charging":
            is_charging = power.BatteryChargeState() not in (
                "Not Charging",
                "Terminated",
            )
            if (
                is_charging
                and round(power.Vbat(), 2) >= _STORAGE_V + _STORAGE_CHARGING_OFFSET_V
            ):
                power.Off()
                self.state = "storage_poweroff"
            self._hardware_power(on=False)
            if not self.screen_blank:
                return True

        elif self.state == "storage_discharging":
            vbat = round(power.Vbat(), 2)
            charge_state = power.BatteryChargeState()
            if self.screen_blank or charge_state not in ("Not Charging", "Terminated"):
                self._update_discharging_leds(0.0)
            else:
                if vbat <= _STORAGE_V - 0.01:
                    self._fading_to_off = True
                if self._fading_to_off:
                    self._update_discharging_leds(0.0, delta)
                    if self._led_b == 0:
                        self._fading_to_off = False
                        self._storage_settle_ms = 0.0
                        self.state = "storage_discharging_settling"
                else:
                    target = max(0.0, min(1.0, (vbat - (_STORAGE_V - 0.01)) / 0.02))
                    self._update_discharging_leds(target, delta)
            if not self.screen_blank:
                return True

        elif self.state == "storage_discharging_settling":
            self._storage_settle_ms += delta
            if self._storage_settle_ms >= 250:
                is_charging = power.BatteryChargeState() not in (
                    "Not Charging",
                    "Terminated",
                )
                vbat = round(power.Vbat(), 2)
                vbat_adj = (
                    round(vbat - _STORAGE_CHARGING_OFFSET_V, 2) if is_charging else vbat
                )
                if vbat_adj <= _STORAGE_V:
                    power.Off()
                    self.state = "storage_poweroff"
                else:
                    self._display_brightness = 0.0
                    self._fading_to_off = False
                    self._led_b = -1
                    self._storage_settle_ms = 0.0
                    self.state = "storage_discharging"
            if not self.screen_blank:
                return True

        return False

    def draw(self, ctx):
        ctx.save()
        if self.state == "menu":
            bg.draw(ctx)
            self.menu.draw(ctx)
        else:
            ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()

            if not self.screen_blank:
                ctx.font_size = 22
                ctx.text_align = ctx.CENTER
                ctx.rgb(0.96, 0.49, 0)
                if self.state in ("poweroff", "storage_poweroff"):
                    status = (
                        "Battery charged."
                        if self.state == "poweroff"
                        else "Battery at storage voltage."
                    )
                    ctx.move_to(0, -50).text("It is now safe to")
                    ctx.move_to(0, -28).text("unplug your badge.")
                    ctx.font_size = 18
                    ctx.move_to(0, 0).text(status)
                    ctx.font_size = 16
                    ctx.rgb(1, 1, 1).move_to(0, 28).text(
                        "Press any key to blank screen."
                    )
                    ctx.move_to(0, 46).text("Press again to restore screen.")
                    ctx.move_to(0, 73).text("Unplug from USB")
                    ctx.move_to(0, 91).text("to power off.")
                elif self.state in ("standby", "charging_poweroff"):
                    battery_line, current_line, state_line = (
                        self._get_standby_power_lines()
                    )
                    if self.state == "standby":
                        ctx.move_to(0, -40).text("Standby")
                        ctx.font_size = 16
                        ctx.rgb(1, 1, 1).move_to(0, -14).text(
                            "Press any key to blank screen."
                        )
                        ctx.move_to(0, 4).text("Press again to restore screen.")
                        ctx.move_to(0, 22).text("Press [Back] to exit standby.")
                    else:
                        ctx.move_to(0, -84).text("Charging...")
                        ctx.font_size = 16
                        ctx.rgb(1, 1, 1).move_to(0, -58).text("Will power off when")
                        ctx.move_to(0, -41).text("charging stops.")
                        ctx.move_to(0, -18).text("Press [Back] to cancel.")
                        ctx.move_to(0, 5).text("Press any key to blank screen.")
                        ctx.move_to(0, 22).text("Press again to restore screen.")
                    ctx.move_to(0, 46).text(battery_line)
                    ctx.move_to(0, 64).text(current_line)
                    ctx.move_to(0, 82).text(state_line)
                else:  # storage_settling, storage_charging, storage_discharging, storage_discharging_settling
                    vbat = round(power.Vbat(), 2)
                    charge_state = power.BatteryChargeState()
                    if self.state == "storage_charging":
                        is_charging = charge_state not in ("Not Charging", "Terminated")
                        action = "Charging"
                        usb_hint = "" if is_charging else "Connect USB to charge"
                        # Voltage reads high while charging so show adjusted estimate
                        vbat_display = (
                            round(vbat - _STORAGE_CHARGING_OFFSET_V, 2)
                            if is_charging
                            else vbat
                        )
                        vbat_note = " (adj)" if is_charging else ""
                    elif self.state == "storage_discharging":
                        action = "Discharging"
                        usb_hint = (
                            "Disconnect USB to discharge"
                            if charge_state != "Not Charging"
                            else ""
                        )
                        vbat_display = vbat
                        vbat_note = ""
                    else:
                        action = "Settling"
                        usb_hint = ""
                        vbat_display = vbat
                        vbat_note = ""
                    ctx.move_to(0, -40).text("Storage Mode")
                    ctx.font_size = 16
                    ctx.rgb(1, 1, 1)
                    ctx.move_to(0, -18).text("Press [Back] to cancel.")
                    ctx.move_to(0, 5).text("Press any key to blank screen.")
                    ctx.move_to(0, 22).text("Press again to restore screen.")
                    if usb_hint:
                        ctx.rgb(0.96, 0.49, 0).move_to(0, 44).text(usb_hint)
                        ctx.rgb(1, 1, 1)
                    ctx.move_to(0, 64).text(f"{action} to {_STORAGE_V:.2f}V")
                    ctx.move_to(0, 82).text(f"Current: {vbat_display:.2f}V{vbat_note}")
            else:
                pass

        ctx.restore()

        self.draw_overlays(ctx)
