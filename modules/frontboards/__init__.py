from app import App
from system.hexpansion.util import read_hexpansion_header, get_hexpansion_block_devices
import vfs


class FrontBoard(App):
    year: int


def mount_frontboard(i2c, readonly=True):
    header = read_hexpansion_header(i2c, eeprom_addr=0x57)
    if header is None:
        return False

    try:
        eep, partition = get_hexpansion_block_devices(i2c, header, addr=0x57)
    except Exception:
        return False

    mountpoint = "/frontboard"

    try:
        vfs.mount(partition, mountpoint, readonly=readonly)
    except OSError:
        return False

    return True
