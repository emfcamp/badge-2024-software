#include "tildagon_hmac.h"
#include "esp_hmac.h"

#include "py/runtime.h"

static mp_obj_t tildagon_hmac_digest(mp_obj_t key_slot, mp_obj_t msg) {
  uint8_t hmac[32];
  hmac_key_id_t key_id = mp_obj_get_int(key_slot);
  
  mp_buffer_info_t bufinfo;
  mp_get_buffer_raise(msg, &bufinfo, MP_BUFFER_READ);

  esp_err_t err = esp_hmac_calculate(key_id, bufinfo.buf, bufinfo.len, hmac);

  if (err == ESP_FAIL) {
    mp_raise_msg(&mp_type_Exception, "HMAC key not provisioned!");
  }

  return mp_obj_new_bytes(hmac, 32);
}

static MP_DEFINE_CONST_FUN_OBJ_2(tildagon_hmac_digest_obj, tildagon_hmac_digest);

static const mp_rom_map_elem_t tildagon_hmac_globals_table[] = {
  { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_HMAC)},
  { MP_ROM_QSTR(MP_QSTR_digest), MP_ROM_PTR(&tildagon_hmac_digest_obj) },
  { MP_ROM_QSTR(MP_QSTR_HMAC_KEY0), MP_ROM_INT(HMAC_KEY0)},
  { MP_ROM_QSTR(MP_QSTR_HMAC_KEY1), MP_ROM_INT(HMAC_KEY1)},
  { MP_ROM_QSTR(MP_QSTR_HMAC_KEY2), MP_ROM_INT(HMAC_KEY2)},
  { MP_ROM_QSTR(MP_QSTR_HMAC_KEY3), MP_ROM_INT(HMAC_KEY3)},
  { MP_ROM_QSTR(MP_QSTR_HMAC_KEY4), MP_ROM_INT(HMAC_KEY4)},
  { MP_ROM_QSTR(MP_QSTR_HMAC_KEY5), MP_ROM_INT(HMAC_KEY5)},
};

static MP_DEFINE_CONST_DICT(tildagon_hmac_globals, tildagon_hmac_globals_table);

const mp_obj_module_t tildagon_hmac_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&tildagon_hmac_globals,
};


MP_REGISTER_MODULE(MP_QSTR_tildagon_hmac, tildagon_hmac_module);