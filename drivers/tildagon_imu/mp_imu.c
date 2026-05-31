
#include "tildagon_imu.h"

#include "py/builtin.h"
#include "py/runtime.h"
#include "esp_err.h"
#include <string.h>

static mp_obj_t mp_imu_acc_read(void) {
    static float x, y, z;

    // Will not overwrite old data if there is an error
    tildagon_imu_acc_read(&x, &y, &z);

    mp_obj_t items[3] = { mp_obj_new_float(x), mp_obj_new_float(y),
                          mp_obj_new_float(z) };
    return mp_obj_new_tuple(3, items);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_acc_read_obj, mp_imu_acc_read);

static mp_obj_t mp_imu_gyro_read(void) {
    static float x, y, z;

    // Will not overwrite old data if there is an error
    tildagon_imu_gyro_read(&x, &y, &z);

    mp_obj_t items[3] = { mp_obj_new_float(x), mp_obj_new_float(y),
                          mp_obj_new_float(z) };
    return mp_obj_new_tuple(3, items);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_gyro_read_obj, mp_imu_gyro_read);

static mp_obj_t mp_imu_step_counter_read(void) {
    static uint32_t steps;

    tildagon_imu_step_counter_read(&steps);

    return mp_obj_new_int_from_uint(steps);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_step_counter_read_obj, mp_imu_step_counter_read);

static mp_obj_t mp_imu_temperature_read(void) {
    static float temperature;

    tildagon_imu_temperature_read(&temperature);

    return mp_obj_new_float_from_f(temperature);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_temperature_read_obj, mp_imu_temperature_read);

static mp_obj_t mp_imu_id(void) {
    static char* id;
    id = tildagon_imu_get_id();
    return mp_obj_new_str(id, strlen(id));
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_id_obj, mp_imu_id);

static mp_obj_t mp_imu_read_from(mp_obj_t reg_address, mp_obj_t length ) {
    uint8_t address = mp_obj_get_int(reg_address);
    uint8_t len = mp_obj_get_int(length);
    uint8_t buffer[len];
    int err = tildagon_imu_read(address, len, buffer);
    if ( err < 0 )
    {
        return mp_obj_new_int(err);
    }
    else
    {
        mp_obj_t buf = mp_obj_new_bytes(buffer, len);
        return buf;
    }
}

static MP_DEFINE_CONST_FUN_OBJ_2(mp_imu_read_from_obj, mp_imu_read_from);

static mp_obj_t mp_imu_write_to(mp_obj_t reg_address, mp_obj_t buffer ) {
    uint8_t address = mp_obj_get_int(reg_address);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(buffer, &bufinfo, MP_BUFFER_READ);
    int err = tildagon_imu_write(address, (uint8_t)bufinfo.len, (uint8_t *)bufinfo.buf);
    if ( err < 0 )
    {
        return mp_obj_new_int(err);
    }
    else
    {
        return mp_const_none;
    }
}

static MP_DEFINE_CONST_FUN_OBJ_2(mp_imu_write_to_obj, mp_imu_write_to);

static const mp_rom_map_elem_t globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_acc_read), MP_ROM_PTR(&mp_imu_acc_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_gyro_read), MP_ROM_PTR(&mp_imu_gyro_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_step_counter_read), MP_ROM_PTR(&mp_imu_step_counter_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_temperature_read), MP_ROM_PTR(&mp_imu_temperature_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_id), MP_ROM_PTR(&mp_imu_id_obj) },
    { MP_ROM_QSTR(MP_QSTR_readfrom), MP_ROM_PTR(&mp_imu_read_from_obj) },
    { MP_ROM_QSTR(MP_QSTR_writeto), MP_ROM_PTR(&mp_imu_write_to_obj) },
};

static MP_DEFINE_CONST_DICT(globals, globals_table);

const mp_obj_module_t mp_module_imu_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&globals,
};

MP_REGISTER_MODULE(MP_QSTR_imu, mp_module_imu_user_cmodule);
