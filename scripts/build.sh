#!/bin/bash
set -e -o pipefail

find /firmware -name '.git' -exec bash -c 'git config --global --add safe.directory ${0%/.git}' {} \;

source /esp-idf/export.sh
export IOT_SOLUTION_PATH=/firmware/esp-iot-solution

cd /firmware
cd micropython
make -C mpy-cross

cd ports/esp32/boards
ln -sfn /firmware/tildagon ./tildagon

cd ..
make submodules BOARD=tildagon USER_C_MODULES=/firmware/drivers/micropython.cmake
make BOARD=tildagon USER_C_MODULES=/firmware/drivers/micropython.cmake $@
