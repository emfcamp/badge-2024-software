from machine import I2C
from system.hexpansion.util import get_hexpansion_block_devices, HexpansionHeader
import vfs
import wifi
import display

base = "/template"

"""
import os, wifi, requests
os.mkdir("/template")
wifi.connect("emf2024", "badge", "badge")
wifi.wait()
for filename in ["tokens.mpy", "app.mpy"]:
    with open(f"/template/{filename}", "wb") as fb_file:
        data = requests.get(f"https://0d3d512069d3.ngrok.app/{filename}")
        print(data.status_code)
        fb_file.write(data.content)
        print(fb_file.tell())
"""


def status(msg=""):
    try:
        ctx = display.get_ctx()
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.text_align = ctx.CENTER
        ctx.font_size = 18.0
        ctx.rgb(1, 1, 1).move_to(0, 0).text("Provisioning ...")
        ctx.rgb(1, 0, 0).move_to(0, 20).text(msg)
        display.end_frame(ctx)
    except Exception:
        pass


def populate_fb():
    status()
    # Ensure the board isn't mounted
    mountpoint = "/frontboard"

    try:
        vfs.umount(mountpoint)
    except OSError:
        pass

    port = 0
    addr = 0x57
    i2c = I2C(port)
    wifi.connect()

    status("Header")

    h = HexpansionHeader(
        manifest_version="2024",
        fs_offset=32,
        eeprom_page_size=32,
        eeprom_total_size=1024 * 8,
        vid=0xBAD3,
        pid=0x2400,
        unique_id=0x0,
        friendly_name="TwentyTwentyFour",
    )

    status("Writing EEPROM")
    # Write header to 0x00 of the eeprom
    i2c.writeto(addr, bytes([0, 0]) + h.to_bytes())

    _, partition = get_hexpansion_block_devices(i2c, h, addr)

    success = True

    status("Creating filesystem")

    vfs.VfsLfs2.mkfs(partition)
    vfs.mount(partition, mountpoint, readonly=False)

    for filename in ["tokens.mpy", "app.mpy"]:
        with open(f"{mountpoint}/{filename}", "wb") as fb_file:
            with open(f"{base}/{filename}", "rb") as template_file:
                fb_file.write(template_file.read())
                if fb_file.tell() != template_file.tell():
                    status("Failed write")
                    success = False

    if not success:
        raise ValueError("Retry")

    status("Remounting")
    vfs.umount(mountpoint)
    vfs.mount(partition, mountpoint, readonly=True)
    status("Done")
