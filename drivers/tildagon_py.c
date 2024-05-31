#include "py/builtin.h"
#include "py/runtime.h"

#if MICROPY_PY_TILDAGON

// info()
static mp_obj_t py_tildagon_info(void) {
    return MP_OBJ_NEW_SMALL_INT(42);
}
MP_DEFINE_CONST_FUN_OBJ_0(tildagon_info_obj, py_tildagon_info);

static const mp_rom_map_elem_t mp_module_tildagon_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tildagon) },
    { MP_ROM_QSTR(MP_QSTR_I2C), MP_ROM_PTR(&tildagon_info_obj) },
};
static MP_DEFINE_CONST_DICT(mp_module_tildagon_globals, mp_module_tildagon_globals_table);

const mp_obj_module_t mp_module_tildagon = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&mp_module_tildagon_globals,
};

MP_REGISTER_MODULE(MP_QSTR_tildagon, mp_module_tildagon);

#endif