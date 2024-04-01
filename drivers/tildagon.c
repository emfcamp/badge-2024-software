#include "tildagon.h"
#include "tildagon_i2c.h"

static tca9548a_i2c_mux_t tildagon_i2c_mux;

const tca9548a_i2c_mux_t *tildagon_get_i2c_mux() {
  if(tildagon_i2c_mux.addr == 0) {
    tildagon_i2c_mux.addr = 0x77;
    
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = TILDAGON_HOST_I2C_SDA,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = TILDAGON_HOST_I2C_SCL,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = TILDAGON_HOST_I2C_FREQ,
    };
    i2c_param_config(TILDAGON_HOST_I2C_PORT, &conf);
    int timeout = I2C_SCLK_FREQ / 1000000 * TILDAGON_HOST_I2C_TIMEOUT;
    i2c_set_timeout(TILDAGON_HOST_I2C_PORT, (timeout > I2C_LL_MAX_TIMEOUT) ? I2C_LL_MAX_TIMEOUT : timeout);
    i2c_driver_install(TILDAGON_HOST_I2C_PORT, I2C_MODE_MASTER, 0, 0, 0);
  }
  return &tildagon_i2c_mux;
}