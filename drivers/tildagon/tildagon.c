#include "py/builtin.h"
#include "py/runtime.h"

// #include "tildagon_hmac/tildagon_hmac.h"

extern const mp_obj_module_t tildagon_hmac_module;


static const mp_rom_map_elem_t mp_module_tildagon_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tildagon) },
    { MP_ROM_QSTR(MP_QSTR_HMAC), MP_ROM_PTR(&tildagon_hmac_module) },
};
static MP_DEFINE_CONST_DICT(mp_module_tildagon_globals, mp_module_tildagon_globals_table);

const mp_obj_module_t mp_module_tildagon = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&mp_module_tildagon_globals,
};

MP_REGISTER_MODULE(MP_QSTR_tildagon, mp_module_tildagon);
