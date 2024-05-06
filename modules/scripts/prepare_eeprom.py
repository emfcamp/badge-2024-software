from machine import I2C
from system.hexpansion.header import HexpansionHeader, write_header
from system.hexpansion.util import (
    detect_eeprom_addr,
    get_hexpansion_block_devices,
    read_hexpansion_header,
)
import vfs
from tildagonos import tildagonos

# Need to init this to make sure i2c works
t = tildagonos()

# Set up i2c
port = 0  # <<-- Customize!!
i2c = I2C(port)

# autodetect eeprom address
addr = detect_eeprom_addr(i2c)
print(f"Detected eeprom at {hex(addr)}")

# Fill in your desired header info here:
header = HexpansionHeader(
    manifest_version="2024",
    fs_offset=32,
    eeprom_page_size=32,
    eeprom_total_size=1024 * 64,
    vid=0xCA75,
    pid=0x1337,
    unique_id=0x0,
    friendly_name="Internal",
)

# Write and read back header
write_header(port, header, addr)
header = read_hexpansion_header(i2c, addr)

# Get block devices
eep, partition = get_hexpansion_block_devices(i2c, header, addr)

# Format
vfs.VfsLfs2.mkfs(partition)

# And mount!
vfs.mount(partition, "/eeprom")
