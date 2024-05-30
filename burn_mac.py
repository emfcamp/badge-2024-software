#!/usr/bin/python

import hashlib
import esptool, espefuse
import os, hmac, time


def burn_hmac_key(key_to_use=1, port=None, do_not_confirm=False):
    # This is the master secret and should be kept secret
    # Initialise it from the environment variable
    MASTER_SECRET = os.environ["MASTER_SECRET"]

    # Fix this in the code to the sha256sum of the master secret
    MASTER_HASH='59a61bdad01d1074a37bc6ee2ae4bac0a424fc2fcfcbdfd0c386d1fdac0d5c7e'

    # PLEASE PLEASE PLEASE DO NOT REMOVE THIS CHECK
    # IF YOU FLASH THE WRONG SECRET TO THE DEVICE IT CAN NEVER BE UNDONE
    if hashlib.sha256(MASTER_SECRET.encode()).hexdigest() != MASTER_HASH:
        print("Master secret does not match")
        raise Exception("Master secret does not match")

    esp=esptool.get_default_connected_device(esptool.get_port_list(), port=port, connect_attempts=1, initial_baud=115200)
    mac_address = esp.read_mac("BASE_MAC")
    mac_str = '-'.join([f"{b:02X}" for b in mac_address])

    print("MAC Address:", mac_str)

    COMBINED_SECRET = MASTER_SECRET + mac_str

    HMAC_KEY = hashlib.sha256(COMBINED_SECRET.encode()).digest()

    test_mac = hmac.digest(HMAC_KEY, b"test", "sha256")
    print(test_mac.hex())

    efuses, operations = espefuse.get_efuses(esp, do_not_confirm=do_not_confirm)
    class Args:
        name_value_pairs = {}
    args = Args()
    args.name_value_pairs[f"KEY_PURPOSE_{key_to_use}"] = 8
    args.name_value_pairs[f"BLOCK_KEY{key_to_use}"] = HMAC_KEY
    print(operations.burn_efuse)
    # operations.burn_efuse(esp, efuses, args)


if __name__ == "__main__":
    _in = input("Burn in a loop? (y/N): ")
    if _in.lower() == "y":
        loop = True
        print("Burning fuses on loop. Press Ctrl+C to stop")
    else:
        print("Burning single fuse, waiting for device.")
    while(True):
        ports = esptool.get_port_list()
        if not ports:
            time.sleep(1)
            continue
        burn_hmac_key(do_not_confirm=loop)
        while esptool.get_port_list():
            time.sleep(1)
        if not loop:
            break
