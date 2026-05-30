import vfs
from machine import I2C
from system.hexpansion.util import (
    detect_eeprom_addr,
    get_hexpansion_block_devices,
    read_hexpansion_header,
    HexpansionHeader,
)
from system.hexpansion.header import write_header


def populate_fb(h, addr_len):
    # Ensure the board isn't mounted
    mountpoint = "/frontboard"

    try:
        vfs.umount(mountpoint)
    except OSError:
        pass

    port = 0
    addr = 0x57
    i2c = I2C(port)

    write_header(0, h, 0x57, addr_len=addr_len, page_size=h.eeprom_page_size)

    _, partition = get_hexpansion_block_devices(i2c, h, addr)

    vfs.VfsLfs2.mkfs(partition)


def detect_frontboard():
    i2c = I2C(0)

    addr, addr_len = detect_eeprom_addr(i2c)
    if addr is not None and addr_len is not None:
        header = read_hexpansion_header(
            i2c, addr, set_read_addr=True, addr_len=addr_len
        )

        if header is None:
            devices = i2c.scan()
            if 0x58 in devices and 0x57 in devices:
                header = HexpansionHeader(
                    manifest_version="2026",
                    fs_offset=32,
                    eeprom_page_size=32,
                    eeprom_total_size=1024 * 8,
                    vid=0xBAD3,
                    pid=0x2600,
                    unique_id=0x0,
                    friendly_name="Spaceagon",
                )
            else:
                header = HexpansionHeader(
                    manifest_version="2024",
                    fs_offset=32,
                    eeprom_page_size=32,
                    eeprom_total_size=1024 * 8,
                    vid=0xBAD3,
                    pid=0x2400,
                    unique_id=0x0,
                    friendly_name="TwentyTwentyFour",
                )
            populate_fb(header, 2)
        return header.pid
    print("No eeprom detected, defaulting to 2024")
    return 0x2400
