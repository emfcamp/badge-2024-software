#!/bin/bash

# Hard resets micropython submodules. Should not touch changes to this repository itself.
# Assumes submodules are initialised.
# scripts/firstTime.sh will need to be rerun after this.

# Use: sudo scripts/hard-reset.sh

cd micropython
git submodule foreach git clean -fdx
git clean -fdx
git reset --hard --recurse-submodules

echo "NOTE: Remember to run scripts/firstTime.sh before trying to compile!"
