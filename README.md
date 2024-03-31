# Tildagon Firmware

## Building

To build with a consistent toolchain, use docker.

From this folder run:

    docker build . -t esp_idf:5.0.4

To make the docker container with the right version of the ESP-IDF for the latest micropython.

Before you build the first time, apply any patches to vendored content:

    ./scripts/firstTime.sh

Then to build the images run:

    docker run -it -v "$(pwd)"/:/firmware esp_idf:5.0.4 TARGET=esp32s3
