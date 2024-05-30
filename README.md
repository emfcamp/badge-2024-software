# Tildagon Firmware

## Building

To build with a consistent toolchain, use docker.

Pull the firmware build image:

    docker pull matthewwilkes/esp_idf:5.2.1

(Or build it yourself, if you prefer):

    docker build . -t matthewwilkes/esp_idf:5.2.1

Initialize submodules:

    git submodule update --init --recursive

To make the docker container with the right version of the ESP-IDF for the latest micropython.

Before you build the first time, apply any patches to vendored content:

    ./scripts/firstTime.sh

Then to build the images run:

    docker run -it --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware matthewwilkes/esp_idf:5.2.1

Alternatively, to flash a badge, ensure it's plugged in and in bootloader mode, then run:

    docker run -it --device /dev/ttyACM0:/dev/ttyUSB0 --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware matthewwilkes/esp_idf:5.2.1 deploy

where /dev/ttyACM0 is the device's endpoint. This value is correct on Linux.

## Contributing

Please install pre-commit to ensure ruff is run:

    python3 -m pip install pre-commit
    pre-commit install
