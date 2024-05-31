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
header = HexpansionHeader(
    manifest_version="2024",
    fs_offset=32,
    eeprom_page_size=16,
    eeprom_total_size=2048,
    vid=0xCAFE,
    pid=0xD15C,
    unique_id=0x0,
    friendly_name="Flopagon",
)

# Determine amount of bytes in internal address
#addr_len = 2 if header.eeprom_total_size > 256 else 1
#print(f"Using {addr_len} bytes for eeprom internal address")

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
