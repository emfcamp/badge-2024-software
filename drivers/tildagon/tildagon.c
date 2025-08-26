#include "py/builtin.h"
#include "py/runtime.h"
#include "tildagon_pin.h"

static const mp_rom_map_elem_t mp_module_egpio_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_egpio) },
    { MP_ROM_QSTR(MP_QSTR_ePin), MP_ROM_PTR(&tildagon_pin_type)}
};
static MP_DEFINE_CONST_DICT(mp_module_egpio_globals, mp_module_egpio_globals_table);

const mp_obj_module_t mp_module_egpio = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&mp_module_egpio_globals,
};

MP_REGISTER_MODULE(MP_QSTR_egpio, mp_module_egpio);
