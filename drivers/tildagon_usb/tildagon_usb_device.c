#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

#include "py/runtime.h"
#include "py/mphal.h"

#include "esp_log.h"

#include "esp_timer.h"
#ifndef NO_QSTR
#include "tinyusb.h"
#include "tusb_cdc_acm.h"
#endif

#include "tildagon_usb_device.h"

#define CDC_ITF TINYUSB_CDC_ACM_0

static uint8_t usb_rx_buf[CONFIG_TINYUSB_CDC_RX_BUFSIZE];

// This is called from FreeRTOS task "tusb_tsk" in espressif__esp_tinyusb (not an ISR).
static void usb_callback_rx(int itf, cdcacm_event_t *event) {
    // espressif__esp_tinyusb places tinyusb rx data onto freertos ringbuffer which
    // this function forwards onto our stdin_ringbuf.
    for (;;) {
        size_t len = 0;
        esp_err_t ret = tinyusb_cdcacm_read(itf, usb_rx_buf, sizeof(usb_rx_buf), &len);
        if (ret != ESP_OK) {
            break;
        }
        if (len == 0) {
            break;
        }
        for (size_t i = 0; i < len; ++i) {
            if (usb_rx_buf[i] == mp_interrupt_char) {
                mp_sched_keyboard_interrupt();
            } else {
                ringbuf_put(&stdin_ringbuf, usb_rx_buf[i]);
            }
        }
        mp_hal_wake_main_task();
    }
}

tinyusb_config_t tusb_cfg = {0};
tinyusb_config_cdcacm_t acm_cfg;

void tildagon_usb_device_start(void) {
    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));

    acm_cfg.usb_dev = TINYUSB_USBDEV_0;
    acm_cfg.cdc_port = CDC_ITF;
    acm_cfg.rx_unread_buf_sz = 256;
    acm_cfg.callback_rx = &usb_callback_rx;
#ifdef MICROPY_HW_USB_CUSTOM_RX_WANTED_CHAR_CB
    acm_cfg.callback_rx_wanted_char = &MICROPY_HW_USB_CUSTOM_RX_WANTED_CHAR_CB;
#endif
#ifdef MICROPY_HW_USB_CUSTOM_LINE_STATE_CB
    acm_cfg.callback_line_state_changed = &MICROPY_HW_USB_CUSTOM_LINE_STATE_CB;
#endif
#ifdef MICROPY_HW_USB_CUSTOM_LINE_CODING_CB
    acm_cfg.callback_line_coding_changed = &MICROPY_HW_USB_CUSTOM_LINE_CODING_CB;
#endif

    ESP_ERROR_CHECK(tusb_cdc_acm_init(&acm_cfg));

    ESP_LOGE("USBD", "Device mode started");
}

void tildagon_usb_device_stop(void) {
    tusb_cdc_acm_deinit(CDC_ITF);

    tinyusb_driver_uninstall();

    ESP_LOGE("USBD", "Device mode stopped");
}
