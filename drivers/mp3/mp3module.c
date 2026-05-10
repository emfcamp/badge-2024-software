// mp3 — minimp3 (public domain) wrapper as a MicroPython user C module.
// Same Python API as the libhelix-mp3 version:
//
//   import mp3
//   mp3.init()                                  -> True/False
//   pcm, frame_bytes, channels, hz, samples = mp3.decode(buf)
//
//   pcm           -> bytes (16-bit signed LE PCM, interleaved if stereo)
//   frame_bytes   -> int (bytes consumed from buf, advance by this amount)
//   channels      -> 1 or 2
//   hz            -> sample rate
//   samples       -> samples per channel (0 if no frame decoded)
//
// minimp3 is single-header, public domain. Includes its own ID3 / sync handling.

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdouble-promotion"
#pragma GCC diagnostic ignored "-Wfloat-conversion"
#pragma GCC diagnostic ignored "-Wunused-but-set-variable"
#define MINIMP3_IMPLEMENTATION
#define MINIMP3_NO_SIMD          // Xtensa LX7 has no SSE/NEON
#define MINIMP3_ONLY_MP3         // strip MP1/MP2, saves flash
#include "minimp3.h"
#pragma GCC diagnostic pop

#include <stdlib.h>
#include <string.h>
#include "py/runtime.h"
#include "py/objstr.h"

static mp3dec_t  mp3_dec;
static int       mp3_inited = 0;
static int16_t  *mp3_pcm    = NULL;

// ----- mp3.init() -----------------------------------------------------------
static mp_obj_t mp3_init(void) {
    if (!mp3_inited) {
        mp3dec_init(&mp3_dec);
        mp3_inited = 1;
    }
    if (mp3_pcm == NULL) {
        mp3_pcm = (int16_t *)malloc(MINIMP3_MAX_SAMPLES_PER_FRAME * sizeof(int16_t));
        if (mp3_pcm == NULL) {
            return mp_const_false;
        }
    }
    return mp_const_true;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mp3_init_obj, mp3_init);

// ----- mp3.deinit() ---------------------------------------------------------
static mp_obj_t mp3_deinit(void) {
    if (mp3_pcm != NULL) {
        free(mp3_pcm);
        mp3_pcm = NULL;
    }
    mp3_inited = 0;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mp3_deinit_obj, mp3_deinit);

// ----- mp3.decode(buf) ------------------------------------------------------
// minimp3 returns:
//   samples > 0           -> frame decoded, info populated, frame_bytes consumed
//   samples == 0, fb > 0  -> ID3/garbage skipped, advance buf by frame_bytes
//   samples == 0, fb == 0 -> insufficient data, caller should append more bytes
static mp_obj_t mp3_decode(mp_obj_t buf_in) {
    if (!mp3_inited || mp3_pcm == NULL) {
        mp_raise_msg(&mp_type_RuntimeError,
                     MP_ERROR_TEXT("mp3.init() not called"));
    }

    mp_buffer_info_t bi;
    mp_get_buffer_raise(buf_in, &bi, MP_BUFFER_READ);

    mp3dec_frame_info_t info;
    memset(&info, 0, sizeof(info));

    int samples = mp3dec_decode_frame(
        &mp3_dec,
        (const uint8_t *)bi.buf,
        (int)bi.len,
        mp3_pcm,
        &info);

    mp_obj_t pcm_bytes;
    if (samples > 0) {
        int total = samples * info.channels;
        pcm_bytes = mp_obj_new_bytes((const byte *)mp3_pcm,
                                      total * sizeof(int16_t));
    } else {
        pcm_bytes = mp_const_empty_bytes;
    }

    mp_obj_t tup[5] = {
        pcm_bytes,
        mp_obj_new_int(info.frame_bytes),
        mp_obj_new_int(info.channels),
        mp_obj_new_int(info.hz),
        mp_obj_new_int(samples),
    };
    return mp_obj_new_tuple(5, tup);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mp3_decode_obj, mp3_decode);

// ----- module table ---------------------------------------------------------
static const mp_rom_map_elem_t mp3_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mp3) },
    { MP_ROM_QSTR(MP_QSTR_init),     MP_ROM_PTR(&mp3_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_deinit),   MP_ROM_PTR(&mp3_deinit_obj) },
    { MP_ROM_QSTR(MP_QSTR_decode),   MP_ROM_PTR(&mp3_decode_obj) },
};
static MP_DEFINE_CONST_DICT(mp3_module_globals, mp3_module_globals_table);

const mp_obj_module_t mp3_user_cmodule = {
    .base    = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&mp3_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_mp3, mp3_user_cmodule);
