#include "esp_log.h"
#include "tildagon_power.h"
#include "tildagon_imu.h"
#include "tildagon_i2c_mpless.h"
#include "tildagon_i2c_manager.h"
#include "tildagon_usb.h"
#include "tildagon_pin_mpless.h"

//static const char *TAG = "board_init";

// This is the default startup handler for ESP32, does VFS and stuff
void boardctrl_startup(void);

void tildagon_startup(void)
{
    // call the micropy default startup - does VFS init on ESP32
    boardctrl_startup();

    //ESP_LOGI(TAG, "i2c_init");
    tildagon_i2c_init();

    //ESP_LOGI(TAG, "i2c_mgr_init");
    tildagon_i2c_mgr_init();

    //ESP_LOGI(TAG, "pins_init");
    tildagon_pins_init();

    //ESP_LOGI(TAG, "power_init");
    tildagon_power_init();

    //ESP_LOGI(TAG, "usb_init");
    tildagon_usb_init();

    //ESP_LOGI(TAG, "imu_init");
    tildagon_imu_init();

    //ESP_LOGI(TAG, "startup complete");
}
