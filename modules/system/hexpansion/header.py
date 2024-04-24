import struct
from machine import I2C


class HexpansionHeader:
    _header_format = '<4s4sHHIHHH10s'
    _magic = 'THEX'

    def __init__(self,
                 manifest_version: str,
                 fs_offset: int,
                 eeprom_page_size: int,
                 eeprom_total_size: int,
                 vid: int,
                 pid: int,
                 unique_id: int,
                 friendly_name: str):
        self.manifest_version = manifest_version
        self.fs_offset = fs_offset
        self.eeprom_page_size = eeprom_page_size
        self.eeprom_total_size = eeprom_total_size
        self.vid = vid
        self.pid = pid
        self.unique_id = unique_id
        self.friendly_name = friendly_name

        self.to_bytes()

    def __str__(self):
        return f'''HexpansionHeader[
    manifest version: {self.manifest_version},
    fs offset: {self.fs_offset},
    eeprom page size: {self.eeprom_page_size},
    eeprom total size: {self.eeprom_total_size},
    vendor id: {'0x' + hex(self.vid)[2:].upper()},
    product id: {'0x' + hex(self.pid)[2:].upper()},
    unique id: {self.unique_id},
    friendly name: {self.friendly_name},
]'''

    def to_bytes(self):
        return struct.pack(
            self._header_format,
            self._magic,
            self.manifest_version,
            self.fs_offset,
            self.eeprom_page_size,
            self.eeprom_total_size,
            self.vid,
            self.pid,
            self.unique_id,
            self.friendly_name,
        )

    @classmethod
    def from_bytes(cls, buf):
        if len(buf) != 32:
            raise RuntimeError("Invalid header length, should be 32")
        if buf[0:4] != b'THEX':
            raise RuntimeError(f"Invalid magic in hexpansion header: {buf[0:4]}")
        if buf[4:8] != b'2024':
            raise RuntimeError("Unknown manifest version. Supported: [2024]")
        unpacked = struct.unpack(cls._header_format, buf)
        return cls(
            manifest_version=unpacked[1].decode().split("\x00")[0],
            fs_offset=unpacked[2],
            eeprom_page_size=unpacked[3],
            eeprom_total_size=unpacked[4],
            vid=unpacked[5],
            pid=unpacked[6],
            unique_id=unpacked[7],
            friendly_name=unpacked[8].decode().split("\x00")[0]
        )


def write_header(port, header):
    i2c = I2C(port)

    # Write header to 0x00 of the eeprom
    i2c.writeto(0x50, bytes([0, 0]) + header.to_bytes())


def read_header(port):
    i2c = I2C(port)

    # Set internal address to 0x00
    i2c.writeto(0x50, bytes([0, 0]))

    header_bytes = i2c.readfrom(0x50, 32)
    header = HexpansionHeader.from_bytes(header_bytes)

    return header


_h = HexpansionHeader(
    manifest_version="2024",
    fs_offset=64,
    eeprom_page_size=64,
    eeprom_total_size=1024 * 64,
    vid=0xCA75,
    pid=0x1337,
    unique_id=0x0,
    friendly_name="booper"
)
