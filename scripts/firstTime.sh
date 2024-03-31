#!/bin/bash

set -e
pushd micropython
git reset --hard
git apply ../patches/micropython.diff
git apply ../patches/i2c.diff
popd