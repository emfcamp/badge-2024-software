from machine import I2C
from eeprom_i2c import EEPROM, T24C256

from eeprom_partition import EEPROMPartition
from system.hexpansion.header import HexpansionHeader

import vfs
import typing


def detect_eeprom_addr(i2c):
    devices = i2c.scan()
    if 0x57 in devices and 0x50 not in devices:
        return 0x57
    if 0x50 in devices:
        return 0x50
    return None


def read_hexpansion_header(i2c, eeprom_addr=0x50) -> typing.Optional[HexpansionHeader]:
    devices = i2c.scan()
    if eeprom_addr not in devices:
        print(f"No device found at {hex(eeprom_addr)}")
        return None

    i2c.writeto(eeprom_addr, bytes([0, 0]))
    header_bytes = i2c.readfrom(eeprom_addr, 32)

    try:
        header = HexpansionHeader.from_bytes(header_bytes)
    except RuntimeError as e:
        print(f"Failed to decode header: {e}")
        return None

    return header


def get_hexpansion_block_devices(i2c, header, addr=0x50):
    eep = EEPROM(i2c=i2c,
                 chip_size=header.eeprom_total_size,
                 page_size=header.eeprom_page_size,
                 addr=addr)

    n_chips = eep._a_bytes // eep._c_bytes

    partition = EEPROMPartition(eep=eep,
                                offset=header.fs_offset,
                                length=(header.eeprom_total_size * n_chips) - header.fs_offset)
    print("eeprom block count:", eep.ioctl(4, None))
    print("partition block count:", partition.ioctl(4, None))
    print("partition block size:", partition.ioctl(5, None))

    return eep, partition
