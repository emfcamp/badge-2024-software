#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BADGE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

WASM_PORT="$BADGE_DIR/micropython/ports/webassembly"
BUILD_DIR="$WASM_PORT/build-tildagon"

make -C "$BADGE_DIR/micropython/mpy-cross" \
    CFLAGS_EXTRA="-Wno-constant-conversion"

rm -rf "$BUILD_DIR"
mkdir -p "$WASM_PORT/modules"

# We use the same manifest as the normal badge firmware to ensure it's as
# accurate as possible. This will include python code that expects to be on
# actual hardware, which we later override with stubs when using the WASM
make -C "$WASM_PORT" \
    BUILD="$BUILD_DIR" \
    USER_C_MODULES="$BADGE_DIR/drivers" \
    FROZEN_MANIFEST="$BADGE_DIR/tildagon/manifest.py"
