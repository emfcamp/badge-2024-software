from system.hexpansion.header import HexpansionHeader
from machine import I2C


def write_header(port, addr=0x50):
    i2c = I2C(port)

    h = HexpansionHeader(
        manifest_version="2024",
        fs_offset=32,
        eeprom_page_size=32,
        eeprom_total_size=1024 * 64,
        vid=0xCA75,
        pid=0x1337,
        unique_id=0x0,
        friendly_name="internal",
    )

    # Write header to 0x00 of the eeprom
    i2c.writeto(addr, bytes([0, 0]) + h.to_bytes())


def read_header(port, addr=0x50):
    i2c = I2C(port)

    # Set internal address to 0x00
    i2c.writeto(addr, bytes([0, 0]))

    header_bytes = i2c.readfrom(addr, 32)
    header = HexpansionHeader.from_bytes(header_bytes)

    return header
