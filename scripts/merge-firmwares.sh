#!/bin/bash
set -e -o pipefail

source ~/.profile

. /opt/esp/entrypoint.sh
cd /firmware/micropython/ports/esp32
python -m esptool --chip esp32s3 -b 460800 merge_bin -o merged-firmware.bin --flash_mode dio --flash_size 8MB --flash_freq 80m 0x0 build-tildagon/bootloader/bootloader.bin 0x8000 build-tildagon/partition_table/partition-table.bin 0xd000 build-tildagon/ota_data_initial.bin 0x10000 build-tildagon/micropython.bin
