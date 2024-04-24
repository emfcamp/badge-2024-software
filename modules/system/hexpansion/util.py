from machine import I2C
from eeprom_i2c import EEPROM, T24C256

from eeprom_partition import EEPROMPartition
from system.hexpansion.header import HexpansionHeader

import vfs


def read_hexpansion_header(i2c, eeprom_addr=0x50) -> HexpansionHeader | None:
    devices = i2c.scan()
    if eeprom_addr not in devices:
        print(f"No device found at {hex(eeprom_addr)}")
        return None

    i2c.writeto(0x50, bytes([0, 0]))
    header_bytes = i2c.readfrom(0x50, 32)

    try:
        header = HexpansionHeader.from_bytes(header_bytes)
    except RuntimeError as e:
        print(f"Failed to decode header: {e}")
        return None

    return header


def get_hexpansion_block_devices(i2c, header):
    eep = EEPROM(i2c=i2c,
                 chip_size=header.eeprom_total_size,
                 page_size=header.eeprom_page_size)
    partition = EEPROMPartition(eep=eep,
                                offset=header.fs_offset,
                                length=header.eeprom_total_size - header.fs_offset)
    print("eeprom block count:", eep.ioctl(4, None))
    print("partition block count:", partition.ioctl(4, None))
    print("partition block size:", partition.ioctl(5, None))

    return eep, partition
