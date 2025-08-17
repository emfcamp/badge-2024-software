#!/bin/bash

# Hard resets submodules.
# Assumes submodules are initialised.
# scripts/firstTime.sh will need to be rerun after this.

# Use: sudo scripts/hard_reset.sh

cd micropython
git submodule foreach git clean -fdx
git clean -fdx
git reset --hard --recurse-submodules