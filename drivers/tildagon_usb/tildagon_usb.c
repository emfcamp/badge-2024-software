#include "driver/gpio.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_task.h"

#define DEBUG_LED GPIO_NUM_35

TaskHandle_t tildagon_usb_task_handle = NULL;

void tildagon_usb_task(void *param __attribute__((__unused__))) {
    // gpio_reset_pin(DEBUG_LED);
    // gpio_set_direction(DEBUG_LED, GPIO_MODE_OUTPUT);

    while(1) {
    //     gpio_set_level(DEBUG_LED, 1);
         vTaskDelay(500 / portTICK_PERIOD_MS);
    //     gpio_set_level(DEBUG_LED, 0);
    //     vTaskDelay(500 / portTICK_PERIOD_MS);
    }
}

void tildagon_usb_init(void) {
    xTaskCreatePinnedToCore(tildagon_usb_task, "usb_task", 1024, NULL, tskIDLE_PRIORITY+3, &tildagon_usb_task_handle, 0);
}