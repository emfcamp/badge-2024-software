#include "py/runtime.h"
#include "py/obj.h"
#include "py/builtin.h"
#include "mp_power_event.h"

static mp_obj_t callbacks[MP_POWER_EVENT_MAX] = { NULL };

void push_event( mp_power_event_t event )
{
    if (  callbacks[event] != NULL )
    {
        mp_sched_schedule(callbacks[event], mp_const_none);
    }
}

static mp_obj_t mp_power_charge_event_set_cb(mp_obj_t cb) 
{
    callbacks[MP_POWER_EVENT_CHARGE] = cb;
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_power_charge_event_set_cb_obj, mp_power_charge_event_set_cb);

static mp_obj_t mp_power_fault_event_set_cb(mp_obj_t cb) 
{
    callbacks[MP_POWER_EVENT_FAULT] = cb;
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_power_fault_event_set_cb_obj, mp_power_fault_event_set_cb);

static mp_obj_t mp_power_host_attach_set_cb(mp_obj_t cb) 
{
    callbacks[MP_POWER_EVENT_HOST_ATTACH] = cb;
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_power_event_host_attach_set_cb_obj, mp_power_host_attach_set_cb);

static mp_obj_t mp_power_host_detach_set_cb(mp_obj_t cb) 
{
    callbacks[MP_POWER_EVENT_HOST_DETACH] = cb;
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_power_event_host_detach_set_cb_obj, mp_power_host_detach_set_cb);

static mp_obj_t mp_power_device_attach_set_cb(mp_obj_t cb) 
{
    callbacks[MP_POWER_EVENT_DEVICE_ATTACH] = cb;
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_power_event_device_attach_set_cb_obj, mp_power_device_attach_set_cb);

static mp_obj_t mp_power_device_detach_set_cb(mp_obj_t cb) 
{
    callbacks[MP_POWER_EVENT_DEVICE_DETACH] = cb;
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_power_event_device_detach_set_cb_obj, mp_power_device_detach_set_cb);

static mp_obj_t mp_power_lanyard_attach_set_cb(mp_obj_t cb) 
{
    callbacks[MP_POWER_EVENT_LANYARD_ATTACH] = cb;
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_power_event_lanyard_attach_set_cb_obj, mp_power_lanyard_attach_set_cb);

static mp_obj_t mp_power_lanyard_detach_set_cb(mp_obj_t cb) 
{
    callbacks[MP_POWER_EVENT_LANYARD_DETACH] = cb;
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_1(mp_power_event_lanyard_detach_set_cb_obj, mp_power_lanyard_detach_set_cb);


static const mp_rom_map_elem_t power_event_globals_table[] = 
{
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_power_event) },
    { MP_ROM_QSTR(MP_QSTR_set_charge_cb), MP_ROM_PTR(&mp_power_charge_event_set_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_fault_cb), MP_ROM_PTR(&mp_power_fault_event_set_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_host_attach_cb), MP_ROM_PTR(&mp_power_event_host_attach_set_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_host_detach_cb), MP_ROM_PTR(&mp_power_event_host_detach_set_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_device_attach_cb), MP_ROM_PTR(&mp_power_event_device_attach_set_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_device_detach_cb), MP_ROM_PTR(&mp_power_event_device_detach_set_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_lanyard_attach_cb), MP_ROM_PTR(&mp_power_event_lanyard_attach_set_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_lanyard_detach_cb), MP_ROM_PTR(&mp_power_event_lanyard_detach_set_cb_obj) },
};

static MP_DEFINE_CONST_DICT(power_event_globals, power_event_globals_table);

const mp_obj_module_t mp_power_events_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&power_event_globals,
};

MP_REGISTER_MODULE(MP_QSTR_power_event, mp_power_events_cmodule);
