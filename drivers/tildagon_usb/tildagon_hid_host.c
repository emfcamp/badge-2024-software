/*
 * HID host interface code, based heavily upon the example:
 * https://github.com/espressif/esp-idf/blob/v5.2.1/examples/peripherals/usb/host/hid/main/hid_host_example.c
 */
#include <string.h>

#include "esp_log.h"
#include "usb/hid_host.h"
#include "usb/hid_usage_keyboard.h"
#include "usb/hid_usage_mouse.h"

#include "py/runtime.h"

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

#include "tildagon_hid_host.h"

static const char *TAG = "HID";

/**
 * @brief HID Protocol string names
 */
static const char *hid_proto_name_str[] = {
    "NONE",
    "KEYBOARD",
    "MOUSE"
};

QueueHandle_t kb_ev_queue = NULL;
typedef struct {
    uint8_t code;
    uint8_t mod;
    bool release;
} kb_event_t;

static mp_obj_t kb_cb = NULL;

typedef struct _tildagon_usb_KeyEvent_obj_t {
    mp_obj_base_t base;
    bool release;
    mp_uint_t modifier;
    mp_uint_t key_code;
} tildagon_usb_KeyEvent_obj_t;

static mp_obj_t tildagon_usb_KeyEvent_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    tildagon_usb_KeyEvent_obj_t *self = mp_obj_malloc(tildagon_usb_KeyEvent_obj_t, type);

    return MP_OBJ_FROM_PTR(self);
}

static void tildagon_usb_KeyEvent_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    if (attr == MP_QSTR_key) {
        tildagon_usb_KeyEvent_obj_t *self = MP_OBJ_TO_PTR(self_in);
        dest[0] = mp_obj_new_int(self->key_code);
    } else if (attr == MP_QSTR_mod) {
        tildagon_usb_KeyEvent_obj_t *self = MP_OBJ_TO_PTR(self_in);
        dest[0] = mp_obj_new_int(self->modifier);
    } else if (attr == MP_QSTR_release) {
        tildagon_usb_KeyEvent_obj_t *self = MP_OBJ_TO_PTR(self_in);
        dest[0] = mp_obj_new_bool(self->release);
    }
}

static const mp_rom_map_elem_t tildagon_usb_KeyEvent_locals_dict_table[] = {

};
static MP_DEFINE_CONST_DICT(tildagon_usb_KeyEvent_locals_dict, tildagon_usb_KeyEvent_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    tildagon_usb_KeyEvent_type,
    MP_QSTR_KeyEvent,
    MP_TYPE_FLAG_NONE,
    make_new, tildagon_usb_KeyEvent_make_new,
    attr, tildagon_usb_KeyEvent_attr,
    locals_dict, &tildagon_usb_KeyEvent_locals_dict
    );


/**
 * @brief Key buffer scan code search.
 *
 * @param[in] src       Pointer to source buffer where to search
 * @param[in] key       Key scancode to search
 * @param[in] length    Size of the source buffer
 */
static inline bool key_found(const uint8_t *const src,
                             uint8_t key,
                             unsigned int length)
{
    for (unsigned int i = 0; i < length; i++) {
        if (src[i] == key) {
            return true;
        }
    }
    return false;
}

/**
 * @brief USB HID Host Keyboard Interface report callback handler
 *
 * @param[in] data    Pointer to input report data buffer
 * @param[in] length  Length of input report data buffer
 */
static void hid_host_keyboard_report_callback(const uint8_t *const data, const int length)
{
    hid_keyboard_input_report_boot_t *kb_report = (hid_keyboard_input_report_boot_t *)data;

    if (length < sizeof(hid_keyboard_input_report_boot_t)) {
        return;
    }

    static uint8_t prev_keys[HID_KEYBOARD_KEY_MAX] = { 0 };
    
    for (int i = 0; i < HID_KEYBOARD_KEY_MAX; i++) {

        // key has been released verification
        if (prev_keys[i] > HID_KEY_ERROR_UNDEFINED &&
                !key_found(kb_report->key, prev_keys[i], HID_KEYBOARD_KEY_MAX)) {
            if (kb_cb) {
                kb_event_t kev;
                kev.code = prev_keys[i];
                kev.mod = 0;
                kev.release = true;
                xQueueSendToBack(kb_ev_queue, &kev, 0);

                mp_sched_schedule(kb_cb, mp_const_none);
            }
        }

        // key has been pressed verification
        if (kb_report->key[i] > HID_KEY_ERROR_UNDEFINED &&
                !key_found(prev_keys, kb_report->key[i], HID_KEYBOARD_KEY_MAX)) {
            if (kb_cb) {
                kb_event_t kev;
                kev.code = kb_report->key[i];
                kev.mod = 0; // kb_report->modifier.val;
                kev.release = false;
                xQueueSendToBack(kb_ev_queue, &kev, 0);
                mp_sched_schedule(kb_cb, mp_const_none);//keyev_obj);
            }
        }
    }

    memcpy(prev_keys, &kb_report->key, HID_KEYBOARD_KEY_MAX);
}

static mp_obj_t tildagon_hid_get_key_event(void) {
    kb_event_t kb_ev;
    if (xQueueReceive(kb_ev_queue, &kb_ev, 0) == pdTRUE) {
        mp_obj_t keyev_obj = tildagon_usb_KeyEvent_make_new(&tildagon_usb_KeyEvent_type, 0, 0, NULL);
        tildagon_usb_KeyEvent_obj_t *keyev = MP_OBJ_TO_PTR(keyev_obj);
        keyev->key_code = kb_ev.code;
        keyev->modifier = kb_ev.mod;
        keyev->release = kb_ev.release;
        return keyev_obj;
    }
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(tildagon_usb_hid_get_kb_event_obj, tildagon_hid_get_key_event);

/**
 * @brief USB HID Host Mouse Interface report callback handler
 *
 * @param[in] data    Pointer to input report data buffer
 * @param[in] length  Length of input report data buffer
 */
static void hid_host_mouse_report_callback(const uint8_t *const data, const int length)
{
    hid_mouse_input_report_boot_t *mouse_report = (hid_mouse_input_report_boot_t *)data;

    if (length < sizeof(hid_mouse_input_report_boot_t)) {
        return;
    }

    static int x_pos = 0;
    static int y_pos = 0;

    // Calculate absolute position from displacement
    x_pos += mouse_report->x_displacement;
    y_pos += mouse_report->y_displacement;

    // TODO: make this a python object and pass it up
    // hid_print_new_device_report_header(HID_PROTOCOL_MOUSE);

    printf("X: %06d\tY: %06d\t|%c|%c|\r",
           x_pos, y_pos,
           (mouse_report->buttons.button1 ? 'o' : ' '),
           (mouse_report->buttons.button2 ? 'o' : ' '));
    fflush(stdout);
}

/**
 * @brief USB HID Host Generic Interface report callback handler
 *
 * 'generic' means anything else than mouse or keyboard
 *
 * @param[in] data    Pointer to input report data buffer
 * @param[in] length  Length of input report data buffer
 */
static void hid_host_generic_report_callback(const uint8_t *const data, const int length)
{
    // TODO: Make this a python object and pass up
    // hid_print_new_device_report_header(HID_PROTOCOL_NONE);
    // for (int i = 0; i < length; i++) {
        // printf("%02X", data[i]);
    // }
    // putchar('\r');
}

/**
 * @brief USB HID Host interface callback
 *
 * @param[in] hid_device_handle  HID Device handle
 * @param[in] event              HID Host interface event
 * @param[in] arg                Pointer to arguments, does not used
 */
void hid_host_interface_callback(hid_host_device_handle_t hid_device_handle,
                                 const hid_host_interface_event_t event,
                                 void *arg)
{
    uint8_t data[64] = { 0 };
    size_t data_length = 0;
    hid_host_dev_params_t dev_params;
    ESP_ERROR_CHECK(hid_host_device_get_params(hid_device_handle, &dev_params));

    switch (event) {
    case HID_HOST_INTERFACE_EVENT_INPUT_REPORT:
        ESP_ERROR_CHECK(hid_host_device_get_raw_input_report_data(hid_device_handle,
                                                                  data,
                                                                  64,
                                                                  &data_length));

        if (HID_SUBCLASS_BOOT_INTERFACE == dev_params.sub_class) {
            if (HID_PROTOCOL_KEYBOARD == dev_params.proto) {
                hid_host_keyboard_report_callback(data, data_length);
            } else if (HID_PROTOCOL_MOUSE == dev_params.proto) {
                hid_host_mouse_report_callback(data, data_length);
            }
        } else {
            hid_host_generic_report_callback(data, data_length);
        }

        break;
    case HID_HOST_INTERFACE_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "HID Device, protocol '%s' DISCONNECTED",
                 hid_proto_name_str[dev_params.proto]);
        ESP_ERROR_CHECK(hid_host_device_close(hid_device_handle));
        break;
    case HID_HOST_INTERFACE_EVENT_TRANSFER_ERROR:
        ESP_LOGI(TAG, "HID Device, protocol '%s' TRANSFER_ERROR",
                 hid_proto_name_str[dev_params.proto]);
        break;
    default:
        ESP_LOGE(TAG, "HID Device, protocol '%s' Unhandled event",
                 hid_proto_name_str[dev_params.proto]);
        break;
    }
}

void hid_host_device_event(hid_host_device_handle_t hid_device_handle,
                           const hid_host_driver_event_t event,
                           void *arg)
{
    hid_host_dev_params_t dev_params;
    ESP_ERROR_CHECK(hid_host_device_get_params(hid_device_handle, &dev_params));

    switch (event) {
    case HID_HOST_DRIVER_EVENT_CONNECTED:
        ESP_LOGI(TAG, "HID Device, protocol '%s' CONNECTED",
                 hid_proto_name_str[dev_params.proto]);

        const hid_host_device_config_t dev_config = {
            .callback = hid_host_interface_callback,
            .callback_arg = NULL
        };

        ESP_ERROR_CHECK(hid_host_device_open(hid_device_handle, &dev_config));
        if (HID_SUBCLASS_BOOT_INTERFACE == dev_params.sub_class) {
            ESP_ERROR_CHECK(hid_class_request_set_protocol(hid_device_handle, HID_REPORT_PROTOCOL_BOOT));
            if (HID_PROTOCOL_KEYBOARD == dev_params.proto) {
                ESP_ERROR_CHECK(hid_class_request_set_idle(hid_device_handle, 0, 0));
            }
        }
        ESP_ERROR_CHECK(hid_host_device_start(hid_device_handle));
        break;
    default:
        break;
    }
}

void hid_host_init(void) {
    kb_ev_queue = xQueueCreate(10, sizeof(kb_event_t));
}

static mp_obj_t tildagon_usb_hid_set_kb_cb(mp_obj_t cb) {
    kb_cb = cb;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_usb_hid_set_kb_cb_obj, tildagon_usb_hid_set_kb_cb);

static const mp_rom_map_elem_t tildagon_usb_hid_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tildagon_hid) },
    { MP_ROM_QSTR(MP_QSTR_set_kb_cb), MP_ROM_PTR(&tildagon_usb_hid_set_kb_cb_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_kb_event), MP_ROM_PTR(&tildagon_usb_hid_get_kb_event_obj) },
    { MP_ROM_QSTR(MP_QSTR_KeyEvent), MP_ROM_PTR(&tildagon_usb_KeyEvent_type) },
};
static MP_DEFINE_CONST_DICT(tildagon_usb_hid_globals, tildagon_usb_hid_globals_table);

const mp_obj_module_t tildagon_usb_hid_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&tildagon_usb_hid_globals,
};

MP_REGISTER_MODULE(MP_QSTR_tildagon_hid, tildagon_usb_hid_cmodule);
