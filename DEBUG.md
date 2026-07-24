# Debugging

The stock firmware runs TinyUSB on the ESP32-S3's only USB PHY, which
disconnects the chip's built-in USB-Serial-JTAG bridge. The USBJTAG board
variant leaves the PHY alone, so OpenOCD and GDB work over the normal
USB-C cable.

Everything below was tested on Arch, with the repository root as working
directory (important for docker mounts). MacOS and windows are untested, expect issues on mac
(see the macOS notes in the README).

## Build and flash

    docker run -it --rm --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware -u $UID -e HOME=/tmp ghcr.io/emfcamp/esp_idf:v5.5.1 BOARD_VARIANT=USBJTAG
    docker run -it --rm --device /dev/ttyACM1:/dev/ttyUSB0 --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware -u $UID -e HOME=/tmp --group-add $(stat -c '%g' /dev/ttyACM1) ghcr.io/emfcamp/esp_idf:v5.5.1 deploy BOARD_VARIANT=USBJTAG

Tweak ports for your setup. Differences from stock:

- The badge enumerates as Espressif's "USB JTAG/serial debug unit"
  (303A:1001) instead of the TiLDAGON CDC device. The REPL is on its
  serial channel (still a `/dev/ttyACM*` port, mpremote works as usual).
- No `machine.USBDevice`.
- The interrupt and task watchdogs are off so breakpoints don't reset
  the badge.

## OpenOCD

OpenOCD needs the USB bus. It also uses host networking so
GDB and telnet can reach ports 3333/4444:

    docker run -it --rm --privileged -v /dev/bus/usb:/dev/bus/usb --network host -v "$(pwd)"/:/firmware -w /firmware --entrypoint /opt/esp/entrypoint.sh ghcr.io/emfcamp/esp_idf:v5.5.1 openocd -f board/esp32s3-builtin.cfg

Leave this running in the background

## GDB

With OpenOCD running, in a second terminal:

    docker run -it --rm --network host -v "$(pwd)"/:/firmware -w /firmware -u $UID -e HOME=/tmp --entrypoint /opt/esp/entrypoint.sh ghcr.io/emfcamp/esp_idf:v5.5.1 xtensa-esp32s3-elf-gdb micropython/ports/esp32/build-tildagon-USBJTAG/micropython.elf -ex 'target extended-remote :3333' -ex 'python import freertos_gdb'

You can then do all your usual gdb shenanigans, plus some freertos specific things:
## FreeRTOS

The image ships Espressif's
[freertos-gdb](https://github.com/espressif/freertos-gdb) extension.
See their page for further examples.

```
(gdb) freertos 
"freertos" must be followed by the name of a subcommand.
List of freertos subcommands:

freertos queue --  Generate a print out of the current queues info.
freertos semaphore --  Generate a print out of the current semaphores info.
freertos task --  Generate a print out of the current tasks and their states.
freertos timer --  Generate a print out of the current timers info.
....
```

## Troubleshooting

### Badge becomes slow after GDB attaches

When GDB connects, OpenOCD configures the SPI0 flash-cache 
controller for single reads at 20 MHz instead of the 
QIO reads at 80 MHz that the bootloader sets up, and everything
becomes horrifically slow and laggy.

To avoid it, append `-c 'gdb_memory_map disable'` to the OpenOCD
command above. GDB then doesn't know where flash is, so software
breakpoints in flash won't work anymore (hardware still should).

This could be an esp-idf tooling bug, not sure if it is fixed in newer
versions. Or we need to tweak the openocd config maybe.

### No symbols

If `info threads` shows a single bare "Remote target" and frames are
`?? ()`, GDB has no usable symbols. Either the ELF path didn't resolve
(run from the repo root and check for "Reading symbols from ..." at
startup) or the ELF doesn't match what's on the badge. Make sure you're 
in the right directory, and rebuild if necessary.