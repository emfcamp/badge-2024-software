import async_helpers
from app import App
from esp32 import Partition
import machine
from app_components.dialog import YesNoDialog
import network
import ota
import ntptime
import requests
import wifi


class OtaUpdate(App):
    def __init__(self):
        self.status = None
        super().__init__()

    async def run(self, render_update):
        self.status = "Checking version"

        try:
            Partition(Partition.RUNNING)
            # current.get_next_update()
        except Exception:
            # Hitting this likely means your partition table is out of date or
            # you're missing ota_data_initial.bin
            # windfow.println("No OTA info!")
            # window.println("USB flash needed")
            self.minimise()
            return

        # lines = window.flow_lines("OTA requires a  charged battery.USB power is    insufficient.")
        # for line in lines:
        #    window.println(line)
        # window.println("")

        version = ota.get_version()
        if version == "HEAD-HASH-NOTFOUND":
            version = "Custom"
        # window.println("Boot: " + current.info()[4])
        # window.println("Next: " + nxt.info()[4])
        # window.println("Version: " + version)
        # window.println()
        # line = window.get_next_line()
        dialog = YesNoDialog([f"Current: {version}", "Check for updates?"], self)
        # Wait for an answer from the dialogue
        if not await dialog.run(render_update):
            self.minimise()
            return
        else:
            self.status = "Connecting"
            await self.connect(render_update)
            self.status = "Connected"
            await self.otaupdate(render_update)

    async def connect(self, render_update):
        # window = self.window
        # line = window.get_next_line()
        ssid = wifi.get_ssid()
        if not ssid:
            print("No WIFI config!")
            return

        if not wifi.status():
            wifi.connect()
            while True:
                print("Connecting to")
                print(f"{ssid}...")
                if wifi.wait():
                    # Returning true means connected
                    break

                # window.println("WiFi timed out", line)
                # window.println("[A] to retry", line + 1)
                dialog = YesNoDialog("Retry connection?", self)
                self.overlays = [dialog]
                # Wait for an answer from the dialogue
                if await dialog.run(render_update):
                    self.overlays = []
                    if wifi.get_sta_status() == network.STAT_CONNECTING:
                        pass  # go round loop and keep waiting
                    else:
                        wifi.disconnect()
                        wifi.connect()
        ntptime.settime()
        print("IP:")
        print(wifi.get_ip())

    async def otaupdate(self, render_update):
        # window = self.window
        # window.println()
        # line = window.get_next_line()
        self.confirmed = False

        retry = True
        while retry:
            # window.clear_from_line(line)
            self.status = "Updating..."

            response = await async_helpers.unblock(
                requests.head,
                render_update,
                "https://github.com/emfcamp/badge-2024-software/releases/download/latest/micropython.bin",
                allow_redirects=False,
            )
            print(response)
            url = response.headers["Location"]

            try:
                result = await async_helpers.unblock(
                    ota.update,
                    render_update,
                    lambda version, val: self.progress(version, val),
                    url,
                )
                retry = False
            except OSError as e:
                print("Error:" + str(e))
                # window.println("Update failed!")
                # window.println("Error {}".format(e.errno))
                # window.println("[A] to retry")
                # if not self.wait_for_a():
                #    result = None
                #    retry = False
            except Exception as e:
                print(e)

        if result:
            # window.println("Updated OK.")
            # window.println("Press [A] to")
            # window.println("reboot and")
            # window.println("finish update.")
            dialog = YesNoDialog("Reboot", self)
            # Wait for an answer from the dialogue
            if await dialog.run(render_update):
                machine.reset()
        else:
            print("Update cancelled")

    def progress(self, version, val):
        # window = self.window
        if not self.confirmed:
            if len(version) > 0:
                if version == ota.get_version():
                    self.status = "No new version"
                    # window.println("available.")
                    return False

                print("New version:")
                print(version)
                # window.println()
                # line = window.get_next_line()
                # window.println("Press [A] to")
                # window.println("confirm update.")
                # if not self.wait_for_a():
                #    print("Cancelling update")
                #    return False

                # Clear confirmation text
                # window.set_next_line(line)
            self.confirmed = True
            # window.println("Updating...")
            # window.println()

        self.version = version
        self.progress_pct = val
        print(version, val)
        # window.progress_bar(window.get_next_line(), val)
        return True

    def draw(self, ctx):
        # print("draw")
        ctx.rgb(1, 0, 0).rectangle(-120, -120, 240, 240).fill()
        if self.status:
            ctx.rgb(1, 1, 1).move_to(-50, 0).text(str(self.status))
        self.draw_overlays(ctx)
