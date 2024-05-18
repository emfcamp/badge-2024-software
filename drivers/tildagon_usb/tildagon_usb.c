#include "py/runtime.h"

#include "driver/gpio.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

#include "esp_log.h"
#include "esp_intr_alloc.h"
#include "usb/usb_host.h"
#include "usb/msc_host.h"

#include "usb/hid_host.h"
#include "usb/hid_usage_keyboard.h"
#include "usb/hid_usage_mouse.h"

#include "tildagon_hid_host.h"

#define DAEMON_TASK_PRIORITY    2

#define DEBUG_LED GPIO_NUM_35
static const char *TAG = "DAEMON";

mp_obj_t msc_connect_cb = NULL;

static QueueHandle_t app_queue;
typedef struct {
    enum {
        APP_QUIT,
        APP_DEVICE_CONNECTED,
        APP_DEVICE_DISCONNECTED,
        APP_EVENT_HID_HOST,
    } id;
    union {
        struct msc_message {
            uint8_t new_device_address;
        } msc_message;
        struct hid_message {
            hid_host_device_handle_t handle;
            hid_host_driver_event_t event;
            void *arg;
        } hid_host_device;
    };
} app_message_t;

static void msc_event_cb(const msc_host_event_t *event, void *arg)
{
    if (event->event == MSC_DEVICE_CONNECTED) {
        ESP_LOGE(TAG, "MSC device connected");
        app_message_t message = {
            .id = APP_DEVICE_CONNECTED,
            .msc_message.new_device_address = event->device.address,
        };
        xQueueSend(app_queue, &message, portMAX_DELAY);
    } else if (event->event == MSC_DEVICE_DISCONNECTED) {
        ESP_LOGE(TAG, "MSC device disconnected");
        app_message_t message = {
            .id = APP_DEVICE_DISCONNECTED,
        };
        xQueueSend(app_queue, &message, portMAX_DELAY);
    }
}

void hid_host_device_callback(hid_host_device_handle_t hid_device_handle,
                              const hid_host_driver_event_t event,
                              void *arg)
{
    const app_message_t evt_queue = {
        .id = APP_EVENT_HID_HOST,
        // HID Host Device related info
        .hid_host_device.handle = hid_device_handle,
        .hid_host_device.event = event,
        .hid_host_device.arg = arg
    };

    if (app_queue) {
        xQueueSend(app_queue, &evt_queue, 0);
    }
}

static void host_lib_daemon_task(void *arg)
{
    SemaphoreHandle_t signaling_sem = (SemaphoreHandle_t)arg;

    ESP_LOGI(TAG, "Installing USB Host Library");
    usb_host_config_t host_config = {
        .skip_phy_setup = false,
        .intr_flags = ESP_INTR_FLAG_LEVEL1,
    };
    ESP_ERROR_CHECK(usb_host_install(&host_config));

    const msc_host_driver_config_t msc_config = {
        .create_backround_task = true,
        .task_priority = 5,
        .stack_size = 4096,
        .callback = msc_event_cb,
    };
    ESP_ERROR_CHECK(msc_host_install(&msc_config));

    /*
    * HID host driver configuration
    * - create background task for handling low level event inside the HID driver
    * - provide the device callback to get new HID Device connection event
    */
    const hid_host_driver_config_t hid_host_driver_config = {
        .create_background_task = true,
        .task_priority = 5,
        .stack_size = 4096,
        .core_id = 0,
        .callback = hid_host_device_callback,
        .callback_arg = NULL
    };

    ESP_ERROR_CHECK(hid_host_install(&hid_host_driver_config));

    bool has_clients = true;
    bool has_devices = true;
    while (has_clients || has_devices) {
        uint32_t event_flags;
        ESP_ERROR_CHECK(usb_host_lib_handle_events(portMAX_DELAY, &event_flags));
        if (event_flags & USB_HOST_LIB_EVENT_FLAGS_NO_CLIENTS) {
            has_clients = false;
        }
        if (event_flags & USB_HOST_LIB_EVENT_FLAGS_ALL_FREE) {
            has_devices = false;
        }
    }
    ESP_LOGI(TAG, "No more clients and devices");

    //Uninstall the USB Host Library
    ESP_ERROR_CHECK(usb_host_uninstall());
    //Wait to be deleted
    xSemaphoreGive(signaling_sem);
    vTaskDelete(NULL);
}

#define DEBUG_LED GPIO_NUM_35

TaskHandle_t tildagon_usb_task_handle = NULL;

void tildagon_usb_task(void *param __attribute__((__unused__))) {
    // gpio_reset_pin(DEBUG_LED);
    // gpio_set_direction(DEBUG_LED, GPIO_MODE_OUTPUT);
    SemaphoreHandle_t signaling_sem = xSemaphoreCreateBinary();

    TaskHandle_t daemon_task_hdl;
    //Create daemon task
    xTaskCreatePinnedToCore(host_lib_daemon_task,
                            "daemon",
                            4096,
                            (void *)signaling_sem,
                            DAEMON_TASK_PRIORITY,
                            &daemon_task_hdl,
                            0);


    msc_host_device_handle_t msc_device = NULL;
    // msc_host_vfs_handle_t vfs_handle = NULL;

    // Perform all example operations in a loop to allow USB reconnections
    while (1) {
        app_message_t msg;
        if (xQueueReceive(app_queue, &msg, pdMS_TO_TICKS(1000)) == pdTRUE) {

            if (msg.id == APP_DEVICE_CONNECTED) {
                // 1. MSC flash drive connected. Open it and map it to Virtual File System
                ESP_ERROR_CHECK(msc_host_install_device(msg.msc_message.new_device_address, &msc_device));
                // const esp_vfs_fat_mount_config_t mount_config = {
                    // .format_if_mount_failed = false,
                    // .max_files = 3,
                    // .allocation_unit_size = 8192,
                // };
                // this won't work with uPy because they both rely on (different) diskio abstractions for FatFs
                // ESP_ERROR_CHECK(msc_host_vfs_register(msc_device, MNT_PATH, &mount_config, &vfs_handle));
                ESP_LOGE(TAG, "Connected!");
                if (msc_connect_cb)
                {
                    mp_sched_schedule(msc_connect_cb, mp_const_none);
                }
            }
            if ((msg.id == APP_DEVICE_DISCONNECTED) || (msg.id == APP_QUIT)) {
                // if (vfs_handle) {
                    // ESP_ERROR_CHECK(msc_host_vfs_unregister(vfs_handle));
                    // vfs_handle = NULL;
                // }
                if (msc_device) {
                    ESP_ERROR_CHECK(msc_host_uninstall_device(msc_device));
                    msc_device = NULL;
                }
                if (msg.id == APP_QUIT) {
                    // This will cause the usb_task to exit
                    ESP_ERROR_CHECK(msc_host_uninstall());
                    break;
                }
            }
            if ((msg.id == APP_EVENT_HID_HOST)) {
                hid_host_device_event(msg.hid_host_device.handle,
                                      msg.hid_host_device.event,
                                      msg.hid_host_device.arg);
            } 
        }
        else
        {
            // ESP_LOGE("USB", "No events");
        }
    }
    vTaskDelete(daemon_task_hdl);
}

void tildagon_usb_init(void) {
    app_queue = xQueueCreate(5, sizeof(app_message_t));
    assert(app_queue);
    hid_host_init();
    xTaskCreatePinnedToCore(tildagon_usb_task, "usb_task", 4096, NULL, tskIDLE_PRIORITY+3, &tildagon_usb_task_handle, 0);
}

// static mp_obj_t tildagon_usb_set_led(mp_obj_t level_obj) {
//     int level = mp_obj_get_int(level_obj);

//     xQueueSendToBack(led_queue, &level, portMAX_DELAY);

//     return mp_obj_new_int(level);
// }
// static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_usb_set_led_obj, tildagon_usb_set_led);

static mp_obj_t tildagon_usb_try_cb(mp_obj_t cb_obj) {
    msc_connect_cb = cb_obj;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_usb_try_cb_obj, tildagon_usb_try_cb);

static const mp_rom_map_elem_t tildagonusb_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tildagonusb) },
    // { MP_ROM_QSTR(MP_QSTR_set_led), MP_ROM_PTR(&tildagon_usb_set_led_obj) },
    { MP_ROM_QSTR(MP_QSTR_try_cb), MP_ROM_PTR(&tildagon_usb_try_cb_obj)},
};
static MP_DEFINE_CONST_DICT(tildagonusb_module_globals, tildagonusb_module_globals_table);

const mp_obj_module_t tildagon_usb_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&tildagonusb_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_tildagonusb, tildagon_usb_cmodule);


// stubs for the usb stuff that needs reimplementing to make usb repl work
void usb_init(void) {

}

void usb_tx_strn(const char *str, size_t len) {

}