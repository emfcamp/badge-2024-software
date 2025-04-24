#!/bin/bash
set -e -o pipefail

find /firmware -name '.git' -exec bash -c 'git config --global --add safe.directory ${0%/.git}' {} \;

cd /firmware
cd micropython
make -C mpy-cross

cd ports/esp32/boards
ln -sfn ../../../../tildagon ./tildagon

cd ..
make submodules BOARD=tildagon USER_C_MODULES=/firmware/drivers/micropython.cmake
make BOARD=tildagon USER_C_MODULES=/firmware/drivers/micropython.cmake $@
