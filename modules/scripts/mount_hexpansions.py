from machine import I2C
from system.hexpansion.util import (
    read_hexpansion_header,
    get_hexpansion_block_devices,
    detect_eeprom_addr,
)
import vfs
import os

for port in range(1, 7):
    print(f"Attempting to mount hexpansion in port: {port}")
    i2c = I2C(port)

    addr, addr_len = detect_eeprom_addr(i2c)
    if addr is None:
        continue
    header = read_hexpansion_header(i2c, eeprom_addr=addr, addr_len=addr_len)
    if header is None:
        continue

    try:
        eep, partition = get_hexpansion_block_devices(i2c, header, addr_len=addr_len)
    except Exception as e:
        print(f"Failed to get block devices for hexpansion {port}: {e}")
        continue

    mountpoint = f"/hexpansion_{port}"

    try:
        vfs.mount(partition, mountpoint)
    except Exception as e:
        print(f"Failed to mount partition for hexpansion {port}: {e}")
        continue

    print(f"Mounted hexpansion {port} at {mountpoint}")
    print(os.statvfs(mountpoint))
    print(os.listdir(mountpoint))
