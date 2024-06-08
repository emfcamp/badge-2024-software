from eeprom_i2c import EEPROM

from eeprom_partition import EEPROMPartition
from system.hexpansion.header import HexpansionHeader

import typing


def detect_eeprom_addr(i2c):
    devices = i2c.scan()
    if 0x57 in devices and 0x50 not in devices:
        return 0x57
    if 0x50 in devices:
        return 0x50
    return None


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

    if set_read_addr:
        addr_bytes = [0] * addr_len
        try:
            i2c.writeto(eeprom_addr, bytes(addr_bytes))
        except OSError:
            # Potentially write protected, and only one address byte
            i2c.writeto(eeprom_addr, bytes([0]))

    header_bytes = i2c.readfrom(eeprom_addr, 32)

    try:
        header = HexpansionHeader.from_bytes(header_bytes)
    except RuntimeError as e:
        print(f"Failed to decode header: {e}")
        return None

    return header


def get_hexpansion_block_devices(i2c, header, addr=0x50):
    eep = EEPROM(
        i2c=i2c,
        chip_size=header.eeprom_total_size,
        page_size=header.eeprom_page_size,
        addr=addr,
        max_chips_count = 1
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
