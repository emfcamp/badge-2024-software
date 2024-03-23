# Tildagon Firmware

## Building

To build with a consistent toolchain, use docker.

Pull the firmware build image:

    docker pull matthewwilkes/esp_idf:5.0.4

(Or build it yourself, if you prefer):

    docker build . -t matthewwilkes/esp_idf:5.0.4

To make the docker container with the right version of the ESP-IDF for the latest micropython.

Then to build the images run:

    docker run -it --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware matthewwilkes/esp_idf:5.0.4

Alternatively, to flash a badge, ensure it's plugged in and in bootloader mode, then run:

    docker run -it --device /dev/ttyACM0:/dev/ttyUSB0 --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware matthewwilkes/esp_idf:5.0.4 deploy

where /dev/ttyACM0 is the device's endpoint. This value is correct on Linux.