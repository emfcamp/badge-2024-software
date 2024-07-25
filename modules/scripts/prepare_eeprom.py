from machine import I2C
from system.hexpansion.header import HexpansionHeader, write_header
from system.hexpansion.util import (
    detect_eeprom_addr,
    get_hexpansion_block_devices,
    read_hexpansion_header,
)
import vfs

# Need to init this to make sure i2c works

# Set up i2c
port = 2  # <<-- Customize!!
i2c = I2C(port)

# autodetect eeprom address
addr, addr_len = detect_eeprom_addr(i2c)
print(f"Detected eeprom at {hex(addr)}")

# Fill in your desired header info here:
# use this one for the M24C16:
header_m24c16 = HexpansionHeader(
    manifest_version="2024",
    fs_offset=32,
    eeprom_page_size=16,
    eeprom_total_size=1024 * (16 // 8),
    vid=0xCA75,
    pid=0x1337,
    unique_id=0,
    friendly_name="M24C16",
)
# use this template for the ZD24C64A
header_zd24c64 = HexpansionHeader(
    manifest_version="2024",
    fs_offset=32,
    eeprom_page_size=32,
    eeprom_total_size=1024 * (64 // 8),
    vid=0xCA75,
    pid=0x1337,
    unique_id=0x0,
    friendly_name="ZD24C64A",
)

header_cat24c512 = HexpansionHeader(
    manifest_version="2024",
    fs_offset=128,
    eeprom_page_size=128,
    eeprom_total_size=1024 * (512 // 8),
    vid=0xCA75,
    pid=0x1337,
    unique_id=0x0,
    friendly_name="CAT24C512",
)

# pick which one to use here
header = header_m24c16

# Write and read back header
write_header(
    port, header, addr=addr, addr_len=addr_len, page_size=header.eeprom_page_size
)
header = read_hexpansion_header(i2c, addr, set_read_addr=True, addr_len=addr_len)

if header is None:
    raise RuntimeError("Failed to read back hexpansion header")

# Get block devices
eep, partition = get_hexpansion_block_devices(i2c, header, addr, addr_len=addr_len)

# Format
vfs.VfsLfs2.mkfs(partition)

# And mount!
vfs.mount(partition, "/eeprom")
