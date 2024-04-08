#ifndef _TCA9548A_H
#define _TCA9548A_H

#include "driver/i2c.h"
#include "hal/i2c_ll.h"

typedef struct _tca9548a_i2c_mux {
  i2c_port_t port : 8;
  uint16_t addr;
  SemaphoreHandle_t mtx;
} tca9548a_i2c_mux_t;

typedef unsigned char tca9548a_i2c_port_t;


/**
 * tca9548a_cmd_link_create
 * 
 * Similar to i2c_cmd_link_create - creates an i2c_cmd_handle_t
 * and additionally performs a transaction to set the downstream port.
 * This function is thread-safe and can be called from any thread.
 * Be aware that a longer timeout may be needed if the bus is busy!
 *
 * @param self - mux object to create the link for
 * @param port - downstream port number to use
*/
i2c_cmd_handle_t tca9548a_cmd_link_create(const tca9548a_i2c_mux_t *self, tca9548a_i2c_port_t port);

/**
 * tca9548a_master_cmd_begin
 *
 * similar to i2c_master_cmd_begin - begins a sequence of I2C transactions
 * on the bus upstream of the i2c mux.
 * 
 * @param self - mux object to begin the i2c transactions for
 * @param cmd - command link to send
 * @param ticks_to_wait - maximum timeout
*/
esp_err_t tca9548a_master_cmd_begin(const tca9548a_i2c_mux_t *self, i2c_cmd_handle_t cmd, TickType_t ticks_to_wait);

/**
 * tca9548a_cmd_set_downstream
 * 
 * Enables the specified downstream port on the I2C provided i2c mux.
 * Only one port is active at a time.
 * 
 * @param self - mux object to set the downstream port for
 * @param port - the port to switch to
*/
esp_err_t tca9548a_cmd_set_downstream(const tca9548a_i2c_mux_t *self, tca9548a_i2c_port_t port);
#endif // _TCA9548A_H