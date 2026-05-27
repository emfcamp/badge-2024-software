
#include "py/runtime.h"
#include "py/obj.h"
#include "py/builtin.h"
#include "mp_frontboard.h"
#include "tildagon_frontboard.h"
#include "cy8cmbrx.h"

/**
 * @brief schedule the micropython callback for the event
 */ 
void mp_frontboard2026_push_event( uint8_t event, uint8_t trigger )
{
    if ( MP_STATE_PORT(callbacks)[event+(trigger*MP_FB_EVENT_MAX)] != NULL )
    {
        mp_sched_schedule(MP_STATE_PORT(callbacks)[event+(trigger*MP_FB_EVENT_MAX)], mp_obj_new_int(event) );
    }
}

/**
 * @brief initialise the frontboard, setting up touch and 
 * proximity and creating the additinal port expander
 */
static mp_obj_t mp_frontboard2026_init( void ) 
{
    tildagon_frontboard_2026_init();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mp_frontboard2026_init_obj, mp_frontboard2026_init);


/**
 * @brief set the callback for both rising and falling 
 * edge of each proximity and touch event
 */
static mp_obj_t mp_frontboard2026_set_cb( mp_obj_t index, mp_obj_t cb, mp_obj_t trigger) 
{
    uint8_t i = mp_obj_get_int( index );
    uint8_t trigger_type = mp_obj_get_int(trigger);
    if ( i < MP_FB_EVENT_MAX )
    {
        MP_STATE_PORT(callbacks)[i+(trigger_type*MP_FB_EVENT_MAX)] = cb;
        return mp_const_none;
    }
    return mp_obj_new_int(-1);
}
static MP_DEFINE_CONST_FUN_OBJ_3(mp_frontboard2026_set_cb_obj, mp_frontboard2026_set_cb);

static mp_obj_t mp_frontboard2026_run( void ) 
{
    cy8cmbrx_cb(NULL, 0);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mp_frontboard2026_run_obj, mp_frontboard2026_run);

static const mp_rom_map_elem_t frontboard2026_globals_table[] = 
{
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_frontboard2026) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mp_frontboard2026_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_cb), MP_ROM_PTR(&mp_frontboard2026_set_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_run), MP_ROM_PTR(&mp_frontboard2026_run_obj) },
    
    { MP_ROM_QSTR(MP_QSTR_TOUCH1), MP_ROM_INT(MP_TOUCH_EVENT_11) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH2), MP_ROM_INT(MP_TOUCH_EVENT_12) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH3), MP_ROM_INT(MP_TOUCH_EVENT_10) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH4), MP_ROM_INT(MP_TOUCH_EVENT_9) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH5), MP_ROM_INT(MP_TOUCH_EVENT_8) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH6), MP_ROM_INT(MP_TOUCH_EVENT_7) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH7), MP_ROM_INT(MP_TOUCH_EVENT_6) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH8), MP_ROM_INT(MP_TOUCH_EVENT_5) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH9), MP_ROM_INT(MP_TOUCH_EVENT_4) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH10), MP_ROM_INT(MP_TOUCH_EVENT_3) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH11), MP_ROM_INT(MP_TOUCH_EVENT_2) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH12), MP_ROM_INT(MP_TOUCH_EVENT_1) },
    { MP_ROM_QSTR(MP_QSTR_PROX1), MP_ROM_INT(MP_PROX_EVENT_1) },
    { MP_ROM_QSTR(MP_QSTR_PROX2), MP_ROM_INT(MP_PROX_EVENT_2) },
    
    { MP_ROM_QSTR(MP_QSTR_IRQ_RISING), MP_ROM_INT(0) },
    { MP_ROM_QSTR(MP_QSTR_IRQ_FALLING), MP_ROM_INT(1) },
};

static MP_DEFINE_CONST_DICT(frontboard2026_globals, frontboard2026_globals_table);

const mp_obj_module_t mp_frontboard2026_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&frontboard2026_globals,
};

MP_REGISTER_MODULE(MP_QSTR_frontboard2026, mp_frontboard2026_cmodule);

MP_REGISTER_ROOT_POINTER(mp_obj_t callbacks[MP_FB_EVENT_MAX*2]);
