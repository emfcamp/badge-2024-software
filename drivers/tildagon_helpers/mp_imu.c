#include "st3m_imu.h"

#include "py/builtin.h"
#include "py/runtime.h"

static mp_obj_t mp_imu_acc_read(void) {
    static float x, y, z;

    // Will not overwrite old data if there is an error
    st3m_imu_read_acc_mps(&x, &y, &z);

    mp_obj_t items[3] = { mp_obj_new_float(x), mp_obj_new_float(y),
                          mp_obj_new_float(z) };
    return mp_obj_new_tuple(3, items);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_acc_read_obj, mp_imu_acc_read);

static mp_obj_t mp_imu_gyro_read(void) {
    static float x, y, z;

    // Will not overwrite old data if there is an error
    st3m_imu_read_gyro_dps(&x, &y, &z);

    mp_obj_t items[3] = { mp_obj_new_float(x), mp_obj_new_float(y),
                          mp_obj_new_float(z) };
    return mp_obj_new_tuple(3, items);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_gyro_read_obj, mp_imu_gyro_read);

static mp_obj_t mp_imu_step_counter_read(void) {
    static uint32_t steps;

    st3m_imu_read_steps(&steps);

    return mp_obj_new_int_from_uint(steps);
}

static MP_DEFINE_CONST_FUN_OBJ_0(mp_imu_step_counter_read_obj, mp_imu_step_counter_read);

static const mp_rom_map_elem_t globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_acc_read), MP_ROM_PTR(&mp_imu_acc_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_gyro_read), MP_ROM_PTR(&mp_imu_gyro_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_step_counter_read), MP_ROM_PTR(&mp_imu_step_counter_read_obj) },
};

static MP_DEFINE_CONST_DICT(globals, globals_table);

const mp_obj_module_t mp_module_imu_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&globals,
};

MP_REGISTER_MODULE(MP_QSTR_imu, mp_module_imu_user_cmodule);
