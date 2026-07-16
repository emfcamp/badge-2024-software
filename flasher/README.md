# Tildagon flasher

First, create a merged firmware binary. This can be done by building as normal, then using:

    docker run -it --entrypoint /firmware/scripts/merge-firmwares.sh --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware -u $UID -e HOME=/tmp ghcr.io/emfcamp/esp_idf:v5.5.1

Then, copy the merged firmware to this directory:

    cp ../micropython/ports/esp32/merged-firmware.bin ./

Now, serve this as HTTP:

    python3 -m http.server 8080

You can then load the flasher from http://localhost:8080

If you are building multiple versions, be careful that the old version isn't cached by your browser.

## Setting up an initial vfs

Prepare a badge with a VFS you want to provision from the factory, and run:

	esptool.py read_flash --flash_size 8MB 0x4f0000 0x310000 ./flasher/sponsors-vfs.bak

