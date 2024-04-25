#!/usr/bin/env bash

set -e -x

# Work around Nix badness.
# See: https://github.com/NixOS/nixpkgs/issues/139943
emscriptenpath="$(dirname $(dirname $(which emcc)))"
if [[ "${emscriptenpath}" = /nix/store/* ]]; then
    if [ ! -d ~/.emscripten_cache ]; then
        cp -rv "$emscriptenpath/share/emscripten/cache" ~/.emscripten_cache
        chmod u+rwX -R ~/.emscripten_cache
    fi
    export EM_CACHE=~/.emscripten_cache
fi


emcc ctx.c \
    -I ../../components/ctx/ \
    -I ../../components/ctx/fonts/ \
    -D SIMULATOR \
    -s EXPORTED_FUNCTIONS=_ctx_new_for_framebuffer,_ctx_new_drawlist,_ctx_parse,_ctx_apply_transform,_ctx_text_width,_ctx_x,_ctx_y,_ctx_render_ctx,_ctx_logo,_ctx_define_texture,_ctx_draw_texture,_ctx_destroy,_stbi_load_from_memory,_malloc,_free \
    --no-entry -flto -O3 \
    -o ctx.wasm

