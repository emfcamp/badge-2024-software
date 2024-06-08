from machine import I2C
from system.hexpansion.util import read_hexpansion_header, get_hexpansion_block_devices, detect_eeprom_addr
import vfs

for port in range(1, 7):
    print(f"Attempting to mount hexpansion in port: {port}")
    i2c = I2C(port)
    addr = detect_eeprom_addr(i2c)

    if addr is None:
        continue
    else:
        print("Found EEPROM at addr " + hex(addr))

    header = read_hexpansion_header(i2c, addr)
    if header is None:
        continue
    else:
        print("Read header: " + str(header))

    try:
        eep, partition = get_hexpansion_block_devices(i2c, header, addr)
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
