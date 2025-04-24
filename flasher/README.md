# Tildagon flasher

First, create a merged firmware binary. This can be done by building as normal, then using:

    docker run -it --entrypoint /firmware/scripts/merge-firmwares.sh --env "TARGET=esp32s3" -v "$(pwd)"/:/firmware -u $UID -e HOME=/tmp matthewwilkes/esp_idf:5.2.3

Then, copy the merged firmware to this directory:

    cp ../micropython/ports/esp32/merged-firmware.bin ./

Now, serve this as HTTP:

    python3 -m http.server 8080

You can then load the flasher from http://localhost:8080
