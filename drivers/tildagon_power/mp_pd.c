#include "py/obj.h"
#include "py/runtime.h"
#include "py/builtin.h"
#include <stdint.h>
#include "tildagon_power.h"


static mp_obj_t pd_get_device_connected( void )
{
    return mp_obj_new_bool(badge_as_device);
}

static MP_DEFINE_CONST_FUN_OBJ_0( pd_get_device_connected_obj, pd_get_device_connected);

static mp_obj_t pd_get_host_connected( void )
{
    return mp_obj_new_bool(badge_as_host);
}

static MP_DEFINE_CONST_FUN_OBJ_0( pd_get_host_connected_obj, pd_get_host_connected);

static mp_obj_t pd_get_device_vendor_msg( void ) 
{
    mp_obj_t tuple[3];
    mp_obj_t buffer = mp_obj_new_list(0, NULL);
    for ( uint8_t i = 0U; i < usb_in.pd.vendor.vendor_data_len; i++)
    {
        mp_obj_list_append(buffer, mp_obj_new_int(usb_in.pd.vendor.vendor_data[i]));
    }
    
    tuple[0] = mp_obj_new_int(usb_in.pd.vendor.vendor_header.all);
    tuple[1] = mp_obj_new_int(usb_in.pd.vendor.vendor_data_len);
    tuple[2] = buffer;
    mp_obj_t result = mp_obj_new_tuple(3, tuple);
    
    usb_in.pd.vendor.vendor_header.all = 0;
    usb_in.pd.vendor.vendor_data_len = 0;
    
    return result;
}

static MP_DEFINE_CONST_FUN_OBJ_0( pd_get_device_vendor_msg_obj, pd_get_device_vendor_msg);

static mp_obj_t pd_get_host_vendor_msg( void ) 
{
    mp_obj_t tuple[3];
    mp_obj_t buffer = mp_obj_new_list(0, NULL);
    for ( uint8_t i = 0U; i < usb_out.pd.vendor.vendor_data_len; i++)
    {
        mp_obj_list_append(buffer, mp_obj_new_int(usb_out.pd.vendor.vendor_data[i]));
    }
    
    tuple[0] = mp_obj_new_int(usb_out.pd.vendor.vendor_header.all);
    tuple[1] = mp_obj_new_int(usb_out.pd.vendor.vendor_data_len);
    tuple[2] = buffer;
    mp_obj_t result = mp_obj_new_tuple(3, tuple);
    
    usb_out.pd.vendor.vendor_header.all = 0;
    usb_out.pd.vendor.vendor_data_len = 0;
    
    return result;
}

static MP_DEFINE_CONST_FUN_OBJ_0( pd_get_host_vendor_msg_obj, pd_get_host_vendor_msg);

static mp_obj_t pd_get_host_prime_msg( void ) 
{
    mp_obj_t tuple[3];
    mp_obj_t buffer = mp_obj_new_list(0, NULL);
    for ( uint8_t i = 0U; i < usb_out.pd.extra->prime.data_size; i++)
    {
        mp_obj_list_append(buffer, mp_obj_new_int(usb_out.pd.extra->prime.data[i]));
    }
    
    tuple[0] = mp_obj_new_int(usb_out.pd.extra->prime.header.all);
    tuple[1] = mp_obj_new_int(usb_out.pd.extra->prime.data_size);
    tuple[2] = buffer;
    mp_obj_t result = mp_obj_new_tuple(3, tuple);
    
    usb_out.pd.extra->prime.header.all = 0;
    usb_out.pd.extra->prime.data_size = 0;
    
    return result;
}

static MP_DEFINE_CONST_FUN_OBJ_0( pd_get_host_prime_msg_obj, pd_get_host_prime_msg);

static mp_obj_t pd_get_host_dbl_prime_msg( void ) 
{
    mp_obj_t tuple[3];
    mp_obj_t buffer = mp_obj_new_list(0, NULL);
    for ( uint8_t i = 0U; i < usb_out.pd.extra->dbl_prime.data_size; i++)
    {
        mp_obj_list_append(buffer, mp_obj_new_int(usb_out.pd.extra->dbl_prime.data[i]));
    }
    tuple[0] = mp_obj_new_int(usb_out.pd.extra->dbl_prime.header.all);
    tuple[1] = mp_obj_new_int(usb_out.pd.extra->dbl_prime.data_size);
    tuple[2] = buffer;
    mp_obj_t result = mp_obj_new_tuple(3, tuple);
    
    usb_out.pd.extra->dbl_prime.header.all = 0;
    usb_out.pd.extra->dbl_prime.data_size = 0;
    
    return result;
}

static MP_DEFINE_CONST_FUN_OBJ_0( pd_get_host_dbl_prime_msg_obj, pd_get_host_dbl_prime_msg);

static mp_obj_t pd_send_device_vendor_msg( mp_obj_t mp_data, mp_obj_t mp_no_objects ) 
{
    mp_buffer_info_t data;
    mp_int_t no_objects;
    mp_get_buffer_raise(mp_data, &data, MP_BUFFER_READ);
    no_objects = mp_obj_get_int(mp_no_objects);
    fusbpd_vendor_specific( &usb_in.pd, data.buf, no_objects );
    fusb_send( &usb_in.fusb, usb_in.pd.tx_buffer, usb_in.pd.message_length );
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_2( pd_send_device_vendor_msg_obj, pd_send_device_vendor_msg);

static mp_obj_t pd_send_host_vendor_msg( mp_obj_t mp_data, mp_obj_t mp_no_objects ) 
{
    mp_buffer_info_t data;
    mp_int_t no_objects;
    mp_get_buffer_raise(mp_data, &data, MP_BUFFER_READ);
    no_objects = mp_obj_get_int(mp_no_objects);
    fusbpd_vendor_specific( &usb_out.pd, data.buf, no_objects );
    fusb_send( &usb_out.fusb, usb_out.pd.tx_buffer, usb_out.pd.message_length );
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_2( pd_send_host_vendor_msg_obj, pd_send_host_vendor_msg);

static mp_obj_t pd_send_host_prime_msg( mp_obj_t mp_header, mp_obj_t mp_data, mp_obj_t mp_length ) 
{
    mp_buffer_info_t data;
    mp_int_t header;
    mp_int_t length;
    mp_get_buffer_raise(mp_data, &data, MP_BUFFER_READ);
    header = mp_obj_get_int(mp_header);
    length = mp_obj_get_int(mp_length);
    fusbpd_prime( &usb_out.pd, header, data.buf, length );
    fusb_send( &usb_out.fusb, usb_out.pd.tx_buffer, usb_out.pd.message_length );
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_3( pd_send_host_prime_msg_obj, pd_send_host_prime_msg);

static mp_obj_t pd_send_host_dbl_prime_msg( mp_obj_t mp_header, mp_obj_t mp_data, mp_obj_t mp_length ) 
{
    mp_buffer_info_t data;
    mp_int_t header;
    mp_int_t length;
    mp_get_buffer_raise(mp_data, &data, MP_BUFFER_READ);
    header = mp_obj_get_int(mp_header);
    length = mp_obj_get_int(mp_length);
    fusbpd_dbl_prime( &usb_out.pd, header, data.buf, length );
    fusb_send( &usb_out.fusb, usb_out.pd.tx_buffer, usb_out.pd.message_length );
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_3( pd_send_host_dbl_prime_msg_obj, pd_send_host_dbl_prime_msg);

static const mp_rom_map_elem_t pd_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pd) },
    { MP_ROM_QSTR(MP_QSTR_get_device_connected), MP_ROM_PTR(&pd_get_device_connected_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_host_connected), MP_ROM_PTR(&pd_get_host_connected_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_device_vendor_msg), MP_ROM_PTR(&pd_get_device_vendor_msg_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_host_vendor_msg), MP_ROM_PTR(&pd_get_host_vendor_msg_obj) },
    // these are untested because of the issue below
    //{ MP_ROM_QSTR(MP_QSTR_get_host_prime_msg), MP_ROM_PTR(&pd_get_host_prime_msg_obj) },
    //{ MP_ROM_QSTR(MP_QSTR_get_host_dbl_prime_msg), MP_ROM_PTR(&pd_get_host_dbl_prime_msg_obj) },
    { MP_ROM_QSTR(MP_QSTR_send_device_vendor_msg), MP_ROM_PTR(&pd_send_device_vendor_msg_obj) },
    { MP_ROM_QSTR(MP_QSTR_send_host_vendor_msg), MP_ROM_PTR(&pd_send_host_vendor_msg_obj) },
    // theres currently an issue with EOP being transmitted before the CRC even though the I2C is correct.
    //{ MP_ROM_QSTR(MP_QSTR_send_host_prime_msg), MP_ROM_PTR(&pd_send_host_prime_msg_obj) },
    //{ MP_ROM_QSTR(MP_QSTR_send_host_dbl_prime_msg), MP_ROM_PTR(&pd_send_host_dbl_prime_msg_obj) },
};

static MP_DEFINE_CONST_DICT( pd_module_globals, pd_module_globals_table );

const mp_obj_module_t pd_user_cmodule = 
{
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&pd_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_pd, pd_user_cmodule);
