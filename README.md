[![Build Micropython](https://github.com/emfcamp/badge-2024-software/actions/workflows/build.yml/badge.svg)](https://github.com/emfcamp/badge-2024-software/actions/workflows/build.yml)

# Tildagon Firmware

Web flasher is available @ https://emfcamp.github.io/badge-2024-software/

## Running from a checkout

Clone the repository including submodules:

    git clone --recursive git@github.com:emfcamp/badge-2024-software.git

Connect your badge via usb, run mpremote to reset, connect to the badge and run the software:

    ./micropython/tools/mpremote/mpremote.py reset; sleep 3; ./micropython/tools/mpremote/mpremote.py mount modules
    import main

NB: mpremote can also be installed separately: https://docs.micropython.org/en/latest/reference/mpremote.html

## Building

To build with a consistent toolchain, use docker.

Pull the firmware build image:

    docker pull matthewwilkes/esp_idf:5.4.1

(Or build it yourself, if you prefer):

    docker build . -t matthewwilkes/esp_idf:5.4.1

Initialize submodules:

    git submodule update --init --recursive

To make the docker container with the right version of the ESP-IDF for the latest micropython.

Before you build the first time, apply any patches to vendored content:

    ./scripts/firstTime.sh

Then to build the images run:

    docker run -it --rm --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware -u $UID -e HOME=/tmp matthewwilkes/esp_idf:5.4.1

Alternatively, to flash a badge:
    put the badge into bootloader by disconnecting the usb in, press and hold bat and boop buttons for 20 seconds  then reconnect the usb in and run:

    docker run -it --rm --device /dev/ttyACM0:/dev/ttyUSB0 --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware -u $UID -e HOME=/tmp matthewwilkes/esp_idf:5.4.1 deploy

where /dev/ttyACM0 is the device's endpoint. This value is correct on Linux.

## Contributing

Please install pre-commit to ensure ruff is run:

    python3 -m pip install pre-commit
    pre-commit install
