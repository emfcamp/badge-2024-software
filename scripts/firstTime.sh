#!/bin/bash

set -e
pushd micropython
git reset --hard
git apply ../patches/micropython.diff
git apply ../patches/usb_host.diff
popd
pushd micropython/lib/micropython-lib
git reset --hard
git apply ../../../patches/micropython-lib.diff
popd