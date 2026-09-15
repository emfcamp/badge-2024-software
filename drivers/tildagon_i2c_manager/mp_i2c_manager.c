#include "tildagon_i2c_manager.h"

#include "py/builtin.h"
#include "py/runtime.h"
#include "py/obj.h"
#include <string.h>

typedef struct _i2c_mgr_job_obj_t {
    mp_obj_base_t base;
    int handle;
} i2c_mgr_job_obj_t;

/* Coalescing flags, packed 1 bit per job rather than a bool per job - not
 * GC-visible, so not a root pointer - just tracks whether a dispatch is
 * already queued for a handle. */
static uint8_t i2c_mgr_job_pending[(TILDAGON_I2C_MGR_MAX_JOBS + 7) / 8];

static inline bool i2c_mgr_pending_get( int handle )
{
    return (i2c_mgr_job_pending[handle / 8] & (1U << (handle % 8))) != 0;
}

static inline void i2c_mgr_pending_set( int handle, bool value )
{
    if ( value )
    {
        i2c_mgr_job_pending[handle / 8] |= (uint8_t)(1U << (handle % 8));
    }
    else
    {
        i2c_mgr_job_pending[handle / 8] &= (uint8_t)~(1U << (handle % 8));
    }
}

/* Runs on the main MicroPython thread via mp_sched_schedule(), never on the
 * manager's background task. Clears the coalescing flag first so a poll
 * that completes while the handler is running schedules a fresh dispatch. */
static mp_obj_t i2c_mgr_irq_dispatch( mp_obj_t handle_in )
{
    mp_int_t handle = mp_obj_get_int( handle_in );
    if ( handle >= 0 && handle < TILDAGON_I2C_MGR_MAX_JOBS )
    {
        i2c_mgr_pending_set( handle, false );
        mp_obj_t handler = MP_STATE_PORT(i2c_mgr_job_irq_handler)[handle];
        if ( handler != MP_OBJ_NULL && handler != mp_const_none )
        {
            mp_call_function_1( handler, MP_STATE_PORT(i2c_mgr_job_wrapper)[handle] );
        }
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1( i2c_mgr_irq_dispatch_obj, i2c_mgr_irq_dispatch );

/* Registered with the C manager via tildagon_i2c_mgr_set_notify() - runs on
 * the manager's background task, so it must not touch the heap or call into
 * MicroPython directly. If a dispatch for this handle is already queued,
 * skip scheduling another one: there is only storage for the most recent
 * sample anyway, so a consumer that hasn't caught up yet loses nothing by
 * missing an intermediate notification, and this is what stops a fast job
 * from flooding the fixed-size scheduler queue that every other feature
 * (e.g. Pin.irq) also shares. */
static void i2c_mgr_job_notify( int handle )
{
    if ( !i2c_mgr_pending_get( handle ) )
    {
        i2c_mgr_pending_set( handle, true );
        if ( !mp_sched_schedule( MP_OBJ_FROM_PTR(&i2c_mgr_irq_dispatch_obj), mp_obj_new_int( handle ) ) )
        {
            i2c_mgr_pending_set( handle, false );
        }
    }
}

static uint16_t i2c_mgr_parse_period( mp_obj_t period_in )
{
    if ( period_in == MP_OBJ_NULL || period_in == mp_const_none )
    {
        return TILDAGON_I2C_MGR_PERIOD_OFF;
    }

    mp_int_t period_ms = mp_obj_get_int( period_in );
    if ( period_ms < (mp_int_t)TILDAGON_I2C_MGR_MIN_PERIOD_MS ||
            period_ms > (mp_int_t)TILDAGON_I2C_MGR_MAX_PERIOD_MS )
    {
        mp_raise_ValueError( MP_ERROR_TEXT("period must be None or 10..65534 ms") );
    }
    return (uint16_t)period_ms;
}

static mp_obj_t i2c_mgr_job_read_into( mp_obj_t self_in, mp_obj_t buf_in )
{
    i2c_mgr_job_obj_t *self = MP_OBJ_TO_PTR( self_in );
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise( buf_in, &bufinfo, MP_BUFFER_WRITE );

    int64_t seq = tildagon_i2c_mgr_read_into( self->handle, (uint8_t *)bufinfo.buf, bufinfo.len );
    if ( seq < 0 )
    {
        return mp_const_none;
    }
    return mp_obj_new_int_from_ull( (unsigned long long)seq );
}
static MP_DEFINE_CONST_FUN_OBJ_2( i2c_mgr_job_read_into_obj, i2c_mgr_job_read_into );

/* job.set_period(period_ms, force=False) */
static mp_obj_t i2c_mgr_job_set_period( size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args )
{
    enum { ARG_period_ms, ARG_force };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_period_ms, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_force, MP_ARG_BOOL, {.u_bool = false} },
    };
    i2c_mgr_job_obj_t *self = MP_OBJ_TO_PTR( pos_args[0] );
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all( n_args - 1, pos_args + 1, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args );

    uint16_t period_ms = i2c_mgr_parse_period( args[ARG_period_ms].u_obj );
    bool force = args[ARG_force].u_bool;
    return mp_obj_new_bool( tildagon_i2c_mgr_set_period( self->handle, period_ms, force ) );
}
static MP_DEFINE_CONST_FUN_OBJ_KW( i2c_mgr_job_set_period_obj, 2, i2c_mgr_job_set_period );

static mp_obj_t i2c_mgr_job_get_period( mp_obj_t self_in )
{
    i2c_mgr_job_obj_t *self = MP_OBJ_TO_PTR( self_in );
    uint16_t period_ms = tildagon_i2c_mgr_get_period( self->handle );
    if ( period_ms == TILDAGON_I2C_MGR_PERIOD_OFF )
    {
        return mp_const_none;
    }
    return mp_obj_new_int_from_uint( period_ms );
}
static MP_DEFINE_CONST_FUN_OBJ_1( i2c_mgr_job_get_period_obj, i2c_mgr_job_get_period );

static mp_obj_t i2c_mgr_job_run_once( mp_obj_t self_in )
{
    i2c_mgr_job_obj_t *self = MP_OBJ_TO_PTR( self_in );
    return mp_obj_new_bool( tildagon_i2c_mgr_run_once( self->handle ) );
}
static MP_DEFINE_CONST_FUN_OBJ_1( i2c_mgr_job_run_once_obj, i2c_mgr_job_run_once );

static mp_obj_t i2c_mgr_job_get_status( mp_obj_t self_in )
{
    i2c_mgr_job_obj_t *self = MP_OBJ_TO_PTR( self_in );
    int status = tildagon_i2c_mgr_get_status( self->handle );
    if ( status < 0 )
    {
        return mp_const_none;
    }
    return mp_obj_new_int( status );
}
static MP_DEFINE_CONST_FUN_OBJ_1( i2c_mgr_job_get_status_obj, i2c_mgr_job_get_status );

static mp_obj_t i2c_mgr_job_unregister( mp_obj_t self_in )
{
    i2c_mgr_job_obj_t *self = MP_OBJ_TO_PTR( self_in );
    if ( self->handle >= 0 )
    {
        tildagon_i2c_mgr_unregister( self->handle );
        MP_STATE_PORT(i2c_mgr_job_irq_handler)[self->handle] = MP_OBJ_NULL;
        MP_STATE_PORT(i2c_mgr_job_wrapper)[self->handle] = MP_OBJ_NULL;
        self->handle = -1;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1( i2c_mgr_job_unregister_obj, i2c_mgr_job_unregister );

/* job.irq(handler) - handler(job) is called once after every poll that
 * publishes new data; pass None (the default) to stop being notified.
 * Multiple completions that occur before the handler gets to run are
 * coalesced into a single call, so the handler should always re-read via
 * read_into() rather than assume exactly one sample per call. */
static mp_obj_t i2c_mgr_job_irq( size_t n_args, const mp_obj_t *args )
{
    i2c_mgr_job_obj_t *self = MP_OBJ_TO_PTR( args[0] );
    if ( self->handle < 0 )
    {
        mp_raise_ValueError( MP_ERROR_TEXT("job is unregistered") );
    }
    mp_obj_t handler = ( n_args > 1 ) ? args[1] : mp_const_none;
    int index = self->handle;
    if ( handler == mp_const_none )
    {
        MP_STATE_PORT(i2c_mgr_job_irq_handler)[index] = MP_OBJ_NULL;
        tildagon_i2c_mgr_set_notify( index, NULL);
    }
    else
    {
        MP_STATE_PORT(i2c_mgr_job_irq_handler)[index] = handler;
        tildagon_i2c_mgr_set_notify( index, i2c_mgr_job_notify);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN( i2c_mgr_job_irq_obj, 1, 2, i2c_mgr_job_irq );

static const mp_rom_map_elem_t i2c_mgr_job_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_read_into), MP_ROM_PTR(&i2c_mgr_job_read_into_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_period), MP_ROM_PTR(&i2c_mgr_job_set_period_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_period), MP_ROM_PTR(&i2c_mgr_job_get_period_obj) },
    { MP_ROM_QSTR(MP_QSTR_run_once), MP_ROM_PTR(&i2c_mgr_job_run_once_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_status), MP_ROM_PTR(&i2c_mgr_job_get_status_obj) },
    { MP_ROM_QSTR(MP_QSTR_irq), MP_ROM_PTR(&i2c_mgr_job_irq_obj) },
    { MP_ROM_QSTR(MP_QSTR_unregister), MP_ROM_PTR(&i2c_mgr_job_unregister_obj) },
};
static MP_DEFINE_CONST_DICT( i2c_mgr_job_locals_dict, i2c_mgr_job_locals_dict_table );

/* Not directly constructable from Python - only produced by add_job(). */
MP_DEFINE_CONST_OBJ_TYPE(
    i2c_mgr_job_type,
    MP_QSTR_Job,
    MP_TYPE_FLAG_NONE,
    locals_dict, &i2c_mgr_job_locals_dict
    );

/* i2c_mgr.add_job(port, addr, steps, period_ms=None, high_priority=False)
 *
 * An active job is due immediately. Due high-priority jobs are dispatched
 * before low-priority jobs, without interrupting an I2C transaction.
 *
 * steps is a tuple/list of step tuples:
 *   (i2c_mgr.READ,  reg, len)
 *   (i2c_mgr.WRITE, reg, len, data)   # data: bytes-like of length len
 *   (i2c_mgr.CHECK, offset, mask, value)
 *
 * Returns a Job object, or None if the job table is full. */
static mp_obj_t i2c_mgr_add_job( size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args )
{
    enum { ARG_port, ARG_addr, ARG_steps, ARG_period_ms, ARG_high_priority };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_port, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_addr, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_steps, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_period_ms, MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_high_priority, MP_ARG_BOOL, {.u_bool = false} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all( n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args );

    if ( args[ARG_port].u_int < 0 || args[ARG_port].u_int > 7 )
    {
        mp_raise_ValueError( MP_ERROR_TEXT("port must be 0..7") );
    }
    if ( args[ARG_addr].u_int < 0 || args[ARG_addr].u_int > 0x7f )
    {
        mp_raise_ValueError( MP_ERROR_TEXT("address must be 7-bit") );
    }

    size_t num_steps;
    mp_obj_t *step_items;
    mp_obj_get_array( args[ARG_steps].u_obj, &num_steps, &step_items );

    if ( num_steps == 0 || num_steps > TILDAGON_I2C_MGR_MAX_STEPS )
    {
        mp_raise_ValueError( MP_ERROR_TEXT("bad step count") );
    }

    tildagon_i2c_mgr_step_t steps[TILDAGON_I2C_MGR_MAX_STEPS];
    memset( steps, 0, sizeof(steps) );

    for ( size_t i = 0; i < num_steps; i++ )
    {
        size_t item_len;
        mp_obj_t *item;
        mp_obj_get_array( step_items[i], &item_len, &item );
        if ( item_len < 3 )
        {
            mp_raise_ValueError( MP_ERROR_TEXT("bad step tuple") );
        }

        mp_int_t type = mp_obj_get_int( item[0] );
        mp_int_t a = mp_obj_get_int( item[1] );
        mp_int_t b = mp_obj_get_int( item[2] );
        if ( type < TILDAGON_I2C_MGR_STEP_READ || type > TILDAGON_I2C_MGR_STEP_WRITE16 ||
             b < 0 || b > UINT8_MAX )
        {
            mp_raise_ValueError( MP_ERROR_TEXT("invalid step field") );
        }
        if ( type == TILDAGON_I2C_MGR_STEP_READ || type == TILDAGON_I2C_MGR_STEP_WRITE )
        {
            if ( a < 0 || a > UINT8_MAX )
            {
                mp_raise_ValueError( MP_ERROR_TEXT("invalid step field") );
            }
        }
        else if ( type == TILDAGON_I2C_MGR_STEP_READ16 || type == TILDAGON_I2C_MGR_STEP_WRITE16 )
        {
            if ( a < 0 || a > UINT16_MAX )
            {
                mp_raise_ValueError( MP_ERROR_TEXT("invalid step field") );
            }
        }
        else if ( type == TILDAGON_I2C_MGR_STEP_CHECK )
        {
            if ( a < 0 || a > UINT8_MAX )
            {
                mp_raise_ValueError( MP_ERROR_TEXT("invalid step field") );
            }
        }
        steps[i].type = (uint8_t)type;
        steps[i].a = (uint16_t)a;
        steps[i].b = (uint8_t)b;

        if ( type == TILDAGON_I2C_MGR_STEP_WRITE || type == TILDAGON_I2C_MGR_STEP_WRITE16 )
        {
            if ( item_len < 4 )
            {
                mp_raise_ValueError( MP_ERROR_TEXT("write step needs data") );
            }
            mp_buffer_info_t bufinfo;
            mp_get_buffer_raise( item[3], &bufinfo, MP_BUFFER_READ );
            if ( bufinfo.len > TILDAGON_I2C_MGR_MAX_STEP_BYTES || bufinfo.len != steps[i].b )
            {
                mp_raise_ValueError( MP_ERROR_TEXT("write step data length mismatch") );
            }
            memcpy( steps[i].data, bufinfo.buf, bufinfo.len );
        }
        else if ( type == TILDAGON_I2C_MGR_STEP_CHECK )
        {
            if ( item_len < 4 )
            {
                mp_raise_ValueError( MP_ERROR_TEXT("check step needs a value") );
            }
            mp_int_t value = mp_obj_get_int( item[3] );
            if ( value < 0 || value > UINT8_MAX )
            {
                mp_raise_ValueError( MP_ERROR_TEXT("check value must be 0..255") );
            }
            steps[i].data[0] = (uint8_t)value;
        }
    }

    uint16_t period_ms = i2c_mgr_parse_period( args[ARG_period_ms].u_obj );

    int handle = tildagon_i2c_mgr_register_steps( (uint8_t)args[ARG_port].u_int, (uint8_t)args[ARG_addr].u_int,
                                                   steps, (uint8_t)num_steps, period_ms,
                                                   args[ARG_high_priority].u_bool );
    if ( handle < 0 )
    {
        return mp_const_none;
    }

    i2c_mgr_job_obj_t *job = mp_obj_malloc( i2c_mgr_job_obj_t, &i2c_mgr_job_type );
    job->handle = handle;
    MP_STATE_PORT(i2c_mgr_job_wrapper)[handle] = MP_OBJ_FROM_PTR( job );
    return MP_OBJ_FROM_PTR( job );
}
static MP_DEFINE_CONST_FUN_OBJ_KW( i2c_mgr_add_job_obj, 3, i2c_mgr_add_job );

static const mp_rom_map_elem_t i2c_mgr_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_add_job), MP_ROM_PTR(&i2c_mgr_add_job_obj) },
    { MP_ROM_QSTR(MP_QSTR_READ), MP_ROM_INT(TILDAGON_I2C_MGR_STEP_READ) },
    { MP_ROM_QSTR(MP_QSTR_WRITE), MP_ROM_INT(TILDAGON_I2C_MGR_STEP_WRITE) },
    { MP_ROM_QSTR(MP_QSTR_CHECK), MP_ROM_INT(TILDAGON_I2C_MGR_STEP_CHECK) },
    { MP_ROM_QSTR(MP_QSTR_READ16), MP_ROM_INT(TILDAGON_I2C_MGR_STEP_READ16) },
    { MP_ROM_QSTR(MP_QSTR_WRITE16), MP_ROM_INT(TILDAGON_I2C_MGR_STEP_WRITE16) },
    { MP_ROM_QSTR(MP_QSTR_OFF), MP_ROM_INT(TILDAGON_I2C_MGR_PERIOD_OFF) },
    { MP_ROM_QSTR(MP_QSTR_MIN_PERIOD_MS), MP_ROM_INT(TILDAGON_I2C_MGR_MIN_PERIOD_MS) },
    { MP_ROM_QSTR(MP_QSTR_STATUS_IDLE), MP_ROM_INT(TILDAGON_I2C_MGR_STATUS_IDLE) },
    { MP_ROM_QSTR(MP_QSTR_STATUS_PENDING), MP_ROM_INT(TILDAGON_I2C_MGR_STATUS_PENDING) },
    { MP_ROM_QSTR(MP_QSTR_STATUS_SUCCESS), MP_ROM_INT(TILDAGON_I2C_MGR_STATUS_SUCCESS) },
    { MP_ROM_QSTR(MP_QSTR_STATUS_CHECK_ABORTED), MP_ROM_INT(TILDAGON_I2C_MGR_STATUS_CHECK_ABORTED) },
    { MP_ROM_QSTR(MP_QSTR_STATUS_I2C_ERROR), MP_ROM_INT(TILDAGON_I2C_MGR_STATUS_I2C_ERROR) },
};
static MP_DEFINE_CONST_DICT( i2c_mgr_globals, i2c_mgr_globals_table );

const mp_obj_module_t mp_module_i2c_mgr_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&i2c_mgr_globals,
};

MP_REGISTER_MODULE(MP_QSTR_i2c_mgr, mp_module_i2c_mgr_user_cmodule);

MP_REGISTER_ROOT_POINTER(mp_obj_t i2c_mgr_job_wrapper[TILDAGON_I2C_MGR_MAX_JOBS]);
MP_REGISTER_ROOT_POINTER(mp_obj_t i2c_mgr_job_irq_handler[TILDAGON_I2C_MGR_MAX_JOBS]);
