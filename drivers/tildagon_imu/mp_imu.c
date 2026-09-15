
#include "tildagon_imu.h"

#include "py/builtin.h"
#include "py/runtime.h"
#include "esp_err.h"
#include <string.h>
#include <stdbool.h>

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

static mp_obj_t mp_imu_mag_read(void) {
    if ( !tildagon_imu_compass_available() )
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("compass is not available on this board"));
    }

    static float x, y, z;

    // Will not overwrite old data if there is an error
    tildagon_imu_compass_read(&x, &y, &z);

    mp_obj_t items[3] = { mp_obj_new_float(x), mp_obj_new_float(y),
                          mp_obj_new_float(z) };
    return mp_obj_new_tuple(3, items);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_mag_read_obj, mp_imu_mag_read);

static mp_obj_t mp_imu_step_counter_read(void) {
    static uint32_t steps;

    tildagon_imu_step_counter_read(&steps);

    return mp_obj_new_int_from_uint(steps);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_step_counter_read_obj, mp_imu_step_counter_read);

static mp_obj_t mp_imu_step_counter_reset(void) {
    tildagon_imu_step_counter_reset();
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_step_counter_reset_obj, mp_imu_step_counter_reset);

static mp_obj_t mp_imu_temperature_read(void) {
    static float temperature;

    tildagon_imu_temperature_read(&temperature);

    return mp_obj_new_float_from_f(temperature);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_temperature_read_obj, mp_imu_temperature_read);

static mp_obj_t mp_imu_id(void) {
    const char* id = tildagon_imu_get_id();
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

// imu.set_period(group, period_ms, force=False)
static mp_obj_t mp_imu_set_period(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_group, ARG_period_ms, ARG_force };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_group, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_period_ms, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_force, MP_ARG_BOOL, {.u_bool = false} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    imu_group_t group = (imu_group_t)args[ARG_group].u_int;
    uint16_t period_ms = TILDAGON_I2C_MGR_PERIOD_OFF;
    if (args[ARG_period_ms].u_obj != mp_const_none) {
        mp_int_t requested_period = mp_obj_get_int(args[ARG_period_ms].u_obj);
        if (requested_period < (mp_int_t)TILDAGON_I2C_MGR_MIN_PERIOD_MS ||
            requested_period > (mp_int_t)TILDAGON_I2C_MGR_MAX_PERIOD_MS) {
            mp_raise_ValueError(MP_ERROR_TEXT("period must be None or 10..65534 ms"));
        }
        period_ms = (uint16_t)requested_period;
    }
    bool force = args[ARG_force].u_bool;
    return mp_obj_new_bool(tildagon_imu_set_period(group, period_ms, force));
}

static MP_DEFINE_CONST_FUN_OBJ_KW(mp_imu_set_period_obj, 2, mp_imu_set_period);

static mp_obj_t mp_imu_get_period(mp_obj_t group) {
    uint16_t period_ms = tildagon_imu_get_period((imu_group_t)mp_obj_get_int(group));
    if (period_ms == TILDAGON_I2C_MGR_PERIOD_OFF) {
        return mp_const_none;
    }
    return mp_obj_new_int_from_uint(period_ms);
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_imu_get_period_obj, mp_imu_get_period);

static const mp_rom_map_elem_t globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_acc_read), MP_ROM_PTR(&mp_imu_acc_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_gyro_read), MP_ROM_PTR(&mp_imu_gyro_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_mag_read), MP_ROM_PTR(&mp_imu_mag_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_step_counter_read), MP_ROM_PTR(&mp_imu_step_counter_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_step_counter_reset), MP_ROM_PTR(&mp_imu_step_counter_reset_obj) },
    { MP_ROM_QSTR(MP_QSTR_temperature_read), MP_ROM_PTR(&mp_imu_temperature_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_id), MP_ROM_PTR(&mp_imu_id_obj) },
    { MP_ROM_QSTR(MP_QSTR_readfrom), MP_ROM_PTR(&mp_imu_read_from_obj) },
    { MP_ROM_QSTR(MP_QSTR_writeto), MP_ROM_PTR(&mp_imu_write_to_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_period), MP_ROM_PTR(&mp_imu_set_period_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_period), MP_ROM_PTR(&mp_imu_get_period_obj) },
    { MP_ROM_QSTR(MP_QSTR_ACCEL_GYRO), MP_ROM_INT(IMU_GROUP_ACCEL_GYRO) },
    { MP_ROM_QSTR(MP_QSTR_TEMPERATURE), MP_ROM_INT(IMU_GROUP_TEMPERATURE) },
    { MP_ROM_QSTR(MP_QSTR_STEPS), MP_ROM_INT(IMU_GROUP_STEPS) },
    { MP_ROM_QSTR(MP_QSTR_COMPASS), MP_ROM_INT(IMU_GROUP_COMPASS) },
    // equivalent to passing None to set_period(); get_period() always returns None (not OFF) when off
    { MP_ROM_QSTR(MP_QSTR_OFF), MP_ROM_INT(TILDAGON_I2C_MGR_PERIOD_OFF) },
};

static MP_DEFINE_CONST_DICT(globals, globals_table);

const mp_obj_module_t mp_module_imu_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&globals,
};

MP_REGISTER_MODULE(MP_QSTR_imu, mp_module_imu_user_cmodule);
