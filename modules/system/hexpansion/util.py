from eeprom_i2c import EEPROM

from eeprom_partition import EEPROMPartition
from system.hexpansion.header import HexpansionHeader
from . import app


import typing


def detect_eeprom_addr(i2c):
    devices = i2c.scan()
    if 0x57 in devices and 0x50 not in devices:
        return (0x57, 2)
    if (
        0x57 in devices
        and 0x56 in devices
        and 0x55 in devices
        and 0x54 in devices
        and 0x53 in devices
        and 0x52 in devices
        and 0x51 in devices
        and 0x50 in devices
    ):
        return (0x50, 1)
    if 0x50 in devices:
        return (0x50, 2)
    return (None, None)


def read_hexpansion_header(
    i2c, eeprom_addr=0x50, set_read_addr=True, addr_len=2
) -> typing.Optional[HexpansionHeader]:
    """
    Read the hexpansion header from the EEPROM on the provided I2C bus, at the specified address.

    @param i2c: An object representing the I2C bus to read from.
    @param eeprom_addr: The address of the EEPROM on the I2C bus. Defaults to 0x50.
    @param set_read_addr: If True, attempts to set the read address before reading.
            Use with caution, as it might overwrite the first byte accidentally on some EEPROMs.
            Defaults to False.
    @param addr_len: The amount of bytes to use for setting the read address.

    @return: A HexpansionHeader object if successful, otherwise None.
    """
    devices = i2c.scan()
    if eeprom_addr not in devices:
        print(f"No device found at {hex(eeprom_addr)}")
        return None

    header_bytes = i2c.readfrom_mem(eeprom_addr, 0, 32, addrsize=addr_len * 8)

    try:
        header = HexpansionHeader.from_bytes(header_bytes)
    except RuntimeError as e:
        print(f"Failed to decode header: {e}")
        return None

    return header


def get_hexpansion_block_devices(i2c, header, addr=0x50, addr_len=2):
    if header.eeprom_total_size > 2 ** (8 * addr_len):
        chip_size = 2 ** (8 * addr_len)
    else:
        chip_size = header.eeprom_total_size
    if header.eeprom_total_size >= 8192:
        block_size = 9  # 512 byte blocks for big EEPROMs
    else:
        block_size = 6  # 64 byte blocks on small EEPROMs
    eep = EEPROM(
        i2c=i2c,
        chip_size=chip_size,
        page_size=header.eeprom_page_size,
        block_size=block_size,
        addrsize=addr_len * 8,
    )
    partition = EEPROMPartition(
        eep=eep,
        offset=header.fs_offset,
        length=header.eeprom_total_size - header.fs_offset,
    )
    print("eeprom block count:", eep.ioctl(4, None))
    print("partition block count:", partition.ioctl(4, None))
    print("partition block size:", partition.ioctl(5, None))

    return eep, partition


def get_slots_by_vid_pid(vid, pid):
    value = []
    for port, header in app._hexpansion_manager.hexpansion_headers.items():
        if header is None:
            continue
        if header.vid == vid and header.pid == pid:
            value.append(port)
    return value


def get_app_by_slot(slot):
    return app._hexpansion_manager.hexpansion_apps.get(slot, None)


def get_app_by_vid_pid(vid, pid):
    slots = get_slots_by_vid_pid(vid, pid)
    if slots:
        return get_app_by_slot(slots[0])
