#!/bin/bash

set -e
pushd micropython
git reset --hard
git apply ../patches/micropython.diff
git apply ../patches/micropython_wasm.diff
git apply ../patches/micropython-i2s-pdm.diff
popd
pushd micropython/lib/micropython-lib
git reset --hard
git apply ../../../patches/micropython-lib.diff
popd
