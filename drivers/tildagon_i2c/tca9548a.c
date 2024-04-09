
#include "driver/i2c.h"
#include "hal/i2c_ll.h"
#include "tca9548a.h"


/**
 * tca9548a_cmd_set_downstream
 * 
 * Enables the specified downstream port on the I2C provided i2c mux.
 * Only one port is active at a time.
 * 
 * @param self - mux object to set the downstream port for
 * @param port - the port to switch to
*/
static esp_err_t tca9548a_cmd_set_downstream(const tca9548a_i2c_mux_t *self, tca9548a_i2c_port_t port, TickType_t ticks_to_wait) {
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();

    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, self->addr << 1, true);
    i2c_master_write_byte(cmd, (1<<port), true);
    i2c_master_stop(cmd);

    esp_err_t ret = i2c_master_cmd_begin(self->port, cmd, ticks_to_wait);
    i2c_cmd_link_delete(cmd);
    return ret;
}

esp_err_t tca9548a_master_cmd_begin(const tca9548a_i2c_mux_t *self, tca9548a_i2c_port_t port, i2c_cmd_handle_t cmd, TickType_t ticks_to_wait) {
    TimeOut_t timeout;
    vTaskSetTimeOutState(&timeout);
    if (pdTRUE != xSemaphoreTake(self->mtx, ticks_to_wait) 
        || pdFALSE != xTaskCheckForTimeOut(&timeout, &ticks_to_wait)) {
      return ESP_ERR_TIMEOUT;
    }
    esp_err_t ret;
    if (port != self->active_port) {
        ret = tca9548a_cmd_set_downstream(self, port, ticks_to_wait);
        if (ret != ESP_OK || pdFALSE != xTaskCheckForTimeOut(&timeout, &ticks_to_wait)) {
            xSemaphoreGive(self->mtx);
            return ret;
        }
        ((tca9548a_i2c_mux_t*)self)->active_port = port;
    }
    ret = i2c_master_cmd_begin(self->port, cmd, ticks_to_wait);
    xSemaphoreGive(self->mtx);
    return ret;
}
