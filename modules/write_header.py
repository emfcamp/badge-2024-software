from apps.indicate_hexpansion import HexpansionHeader
from machine import I2C


def write_header(port):
    i2c = I2C(port)

    h = HexpansionHeader(
        manifest_version="2024",
        fs_offset=64,
        eeprom_page_size=64,
        eeprom_total_size=1024 * 64,
        vid=0xCA75,
        pid=0x1337,
        unique_id=0x0,
        friendly_name="booper"
    )

    # Write header to 0x00 of the eeprom
    i2c.writeto(0x50, bytes([0, 0]) + h.to_bytes())

def read_header(port):
    i2c = I2C(port)

    # Set internal address to 0x00
    i2c.writeto(0x50, bytes([0, 0]))

    header_bytes = i2c.readfrom(0x50, 32)
    header = HexpansionHeader.from_bytes(header_bytes)

    return header
