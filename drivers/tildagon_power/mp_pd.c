#include "py/obj.h"
#include "py/runtime.h"
#include "py/builtin.h"
#include <stdint.h>
#include "tildagon_power.h"


typedef struct _device_obj_t {
    mp_obj_base_t base;
} _device_obj_t;

typedef struct _host_obj_t {
    mp_obj_base_t base;
} _host_obj_t;

static mp_obj_t device_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    _device_obj_t *self = mp_obj_malloc(_device_obj_t, type);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t host_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) 
{
    _host_obj_t *self = mp_obj_malloc(_host_obj_t, type);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t device_pd_enabled( mp_obj_t self_in )
{
    return mp_obj_new_bool( device_pd_state == WAITING );
}

static MP_DEFINE_CONST_FUN_OBJ_1(device_pd_enabled_obj, device_pd_enabled);

static mp_obj_t host_pd_enabled( mp_obj_t self_in )
{
    return mp_obj_new_bool( host_pd_state == WAITING );
}

static MP_DEFINE_CONST_FUN_OBJ_1(host_pd_enabled_obj, host_pd_enabled);

static mp_obj_t device_connected( mp_obj_t self_in )
{
    return mp_obj_new_bool( device_attach_state == ATTACHED );
}

static MP_DEFINE_CONST_FUN_OBJ_1(device_connected_obj, device_connected);

static mp_obj_t host_connected( mp_obj_t self_in )
{
    return mp_obj_new_bool( host_attach_state == ATTACHED );
}

static MP_DEFINE_CONST_FUN_OBJ_1(host_connected_obj, host_connected);

static mp_obj_t device_badge_connected( mp_obj_t self_in )
{
    return mp_obj_new_bool( badge_as_device );
}

static MP_DEFINE_CONST_FUN_OBJ_1(device_badge_connected_obj, device_badge_connected);

static mp_obj_t host_badge_connected( mp_obj_t self_in )
{
    return mp_obj_new_bool( badge_as_host );
}

static MP_DEFINE_CONST_FUN_OBJ_1(host_badge_connected_obj, host_badge_connected);

static mp_obj_t device_get_vendor_msg( mp_obj_t self_in ) 
{
    mp_obj_t buffer = mp_obj_new_list( 0, NULL );
    for ( uint8_t i = 0U; i < ( usb_in.pd.vendor.no_objects * 4); i++ )
    {
        mp_obj_list_append( buffer, mp_obj_new_int( usb_in.pd.vendor.vendor_data[i] ) );
    }
        
    usb_in.pd.vendor.no_objects = 0;
    return buffer;
}

static MP_DEFINE_CONST_FUN_OBJ_1(device_get_vendor_msg_obj, device_get_vendor_msg);

static mp_obj_t host_get_vendor_msg( mp_obj_t self_in ) 
{
    mp_obj_t buffer = mp_obj_new_list( 0, NULL );
    for ( uint8_t i = 0U; i < ( usb_out.pd.vendor.no_objects * 4 ); i++ )
    {
        mp_obj_list_append( buffer, mp_obj_new_int( usb_out.pd.vendor.vendor_data[i] ) );
    }

    usb_out.pd.vendor.no_objects = 0;    
    return buffer;
}

static MP_DEFINE_CONST_FUN_OBJ_1(host_get_vendor_msg_obj, host_get_vendor_msg);

static mp_obj_t host_get_prime_msg( mp_obj_t self_in ) 
{
    mp_obj_t buffer = mp_obj_new_list(0, NULL);
    for ( uint8_t i = 0U; i < usb_out.pd.extra->prime.data_size; i++)
    {
        mp_obj_list_append(buffer, mp_obj_new_int(usb_out.pd.extra->prime.data[i]));
    }
    
    usb_out.pd.extra->prime.data_size = 0;
    
    return buffer;
}

static MP_DEFINE_CONST_FUN_OBJ_1( host_get_prime_msg_obj, host_get_prime_msg);

static mp_obj_t host_get_dbl_prime_msg( mp_obj_t self_in ) 
{
    mp_obj_t buffer = mp_obj_new_list(0, NULL);
    for ( uint8_t i = 0U; i < usb_out.pd.extra->dbl_prime.data_size; i++)
    {
        mp_obj_list_append(buffer, mp_obj_new_int(usb_out.pd.extra->dbl_prime.data[i]));
    }
    
    usb_out.pd.extra->dbl_prime.data_size = 0;
    
    return buffer;
}

static MP_DEFINE_CONST_FUN_OBJ_1( host_get_dbl_prime_msg_obj, host_get_dbl_prime_msg);

static mp_obj_t device_send_vendor_msg( mp_obj_t self_in, mp_obj_t mp_data ) 
{
    mp_buffer_info_t data;
    mp_get_buffer_raise( mp_data, &data, MP_BUFFER_READ );
    if( data.len > 28 )
    {
        return mp_obj_new_int(-ESP_ERR_INVALID_SIZE);
    }
    if( device_pd_state != WAITING )
    {
        return mp_obj_new_int(-ESP_ERR_INVALID_STATE);
    }
    if (data.len % 4)
    {
        /* pad to 4 byte boundry */
        uint8_t buffer[28] = { 0 };
        for (uint8_t i = 0; i < data.len; i++)
        {
            buffer[i] = ((uint8_t*)data.buf)[i];
        }
        fusbpd_vendor_specific( &usb_in.pd, buffer, ( data.len / 4 ) + 1 );
    }
    else
    {
        fusbpd_vendor_specific( &usb_in.pd, data.buf, data.len / 4 );
    }    
    
    fusb_send( &usb_in.fusb, usb_in.pd.tx_buffer, usb_in.pd.message_length );
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_2(device_send_vendor_msg_obj, device_send_vendor_msg);

static mp_obj_t host_send_vendor_msg( mp_obj_t self_in, mp_obj_t mp_data ) 
{
    mp_buffer_info_t data;
    mp_get_buffer_raise( mp_data, &data, MP_BUFFER_READ );
    if( data.len > 28 )
    {
        return mp_obj_new_int(-ESP_ERR_INVALID_SIZE);
    }
    if( host_pd_state != WAITING )
    {
        return mp_obj_new_int(ESP_ERR_INVALID_STATE);
    }
    if (data.len % 4)
    {
        /* pad to 4 byte boundry */
        uint8_t buffer[28] = { 0 };
        for (uint8_t i = 0; i < data.len; i++)
        {
            buffer[i] = ((uint8_t*)data.buf)[i];
        }
        fusbpd_vendor_specific( &usb_out.pd, buffer, ( data.len / 4 ) + 1 );
    }
    else
    {
        fusbpd_vendor_specific( &usb_out.pd, data.buf, data.len / 4 );
    }    
    
    fusb_send( &usb_out.fusb, usb_out.pd.tx_buffer, usb_out.pd.message_length );
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_2(host_send_vendor_msg_obj, host_send_vendor_msg);

static mp_obj_t host_send_prime_msg( mp_obj_t self_in, mp_obj_t mp_data ) 
{
    mp_buffer_info_t data;
    mp_get_buffer_raise(mp_data, &data, MP_BUFFER_READ);
    fusbpd_prime( &usb_out.pd, data.buf, data.len );
    fusb_send( &usb_out.fusb, usb_out.pd.tx_buffer, usb_out.pd.message_length );
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_2( host_send_prime_msg_obj, host_send_prime_msg);

static mp_obj_t host_send_dbl_prime_msg( mp_obj_t self_in, mp_obj_t mp_data ) 
{
    mp_buffer_info_t data;
    mp_get_buffer_raise(mp_data, &data, MP_BUFFER_READ);
    fusbpd_dbl_prime( &usb_out.pd, data.buf, data.len );
    fusb_send( &usb_out.fusb, usb_out.pd.tx_buffer, usb_out.pd.message_length );
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_2( host_send_dbl_prime_msg_obj, host_send_dbl_prime_msg);


static const mp_rom_map_elem_t device_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_connected), MP_ROM_PTR(&device_connected_obj) },
    { MP_ROM_QSTR(MP_QSTR_pd_enabled), MP_ROM_PTR(&device_pd_enabled_obj) },
    { MP_ROM_QSTR(MP_QSTR_badge_connected), MP_ROM_PTR(&device_badge_connected_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_vendor_msg), MP_ROM_PTR(&device_get_vendor_msg_obj) },
    { MP_ROM_QSTR(MP_QSTR_send_vendor_msg), MP_ROM_PTR(&device_send_vendor_msg_obj) },
};

static MP_DEFINE_CONST_DICT(device_locals_dict, device_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    class_type_Device,
    MP_QSTR_Device,
    MP_TYPE_FLAG_NONE,
    make_new, device_make_new,
    locals_dict, &device_locals_dict
    );

static const mp_rom_map_elem_t host_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_connected), MP_ROM_PTR(&host_connected_obj) },
    { MP_ROM_QSTR(MP_QSTR_pd_enabled), MP_ROM_PTR(&host_pd_enabled_obj) },
    { MP_ROM_QSTR(MP_QSTR_badge_connected), MP_ROM_PTR(&host_badge_connected_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_vendor_msg), MP_ROM_PTR(&host_get_vendor_msg_obj) },
    { MP_ROM_QSTR(MP_QSTR_send_vendor_msg), MP_ROM_PTR(&host_send_vendor_msg_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_prime_msg), MP_ROM_PTR(&host_get_prime_msg_obj ) },
    { MP_ROM_QSTR(MP_QSTR_get_dbl_prime_msg), MP_ROM_PTR(&host_get_dbl_prime_msg_obj ) },
    { MP_ROM_QSTR(MP_QSTR_send_prime_msg), MP_ROM_PTR(&host_send_prime_msg_obj ) },
    { MP_ROM_QSTR(MP_QSTR_send_dbl_prime_msg), MP_ROM_PTR(&host_send_dbl_prime_msg_obj ) },
};

static MP_DEFINE_CONST_DICT(host_locals_dict, host_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    class_type_Host,
    MP_QSTR_Host,
    MP_TYPE_FLAG_NONE,
    make_new, host_make_new,
    locals_dict, &host_locals_dict
    );

static const mp_rom_map_elem_t pd_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pd) },
    { MP_ROM_QSTR(MP_QSTR_Device), MP_ROM_PTR(&class_type_Device) },
    { MP_ROM_QSTR(MP_QSTR_Host), MP_ROM_PTR(&class_type_Host) },
};

static MP_DEFINE_CONST_DICT(pd_module_globals, pd_module_globals_table);

const mp_obj_module_t pd_user_cmodule = 
{
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&pd_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_pd, pd_user_cmodule);
