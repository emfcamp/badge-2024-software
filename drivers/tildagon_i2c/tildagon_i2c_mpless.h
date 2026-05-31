#pragma once

#include <stdint.h>
#include "esp_err.h"

#define TILDAGON_HOST_I2C_SDA (45)
#define TILDAGON_HOST_I2C_SCL (46)
#define TILDAGON_HOST_I2C_FREQ (133000)
#define TILDAGON_HOST_I2C_PORT (0)
#define TILDAGON_HOST_I2C_TIMEOUT (50000)

#define TILDAGON_TOP_I2C_PORT (0)
#define TILDAGON_HX0_I2C_PORT (1)
#define TILDAGON_HX1_I2C_PORT (2)
#define TILDAGON_HX2_I2C_PORT (3)
#define TILDAGON_HX3_I2C_PORT (4)
#define TILDAGON_HX4_I2C_PORT (5)
#define TILDAGON_HX5_I2C_PORT (6)
#define TILDAGON_SYS_I2C_PORT (7)

void tildagon_i2c_init(void);

// Write reg_addr then read len bytes from addr on the given mux port.
esp_err_t tildagon_i2c_reg_read(uint8_t port, uint16_t addr, uint8_t reg_addr, uint8_t *data, uint32_t len);

// Write reg_addr followed by len bytes to addr on the given mux port.
esp_err_t tildagon_i2c_reg_write(uint8_t port, uint16_t addr, uint8_t reg_addr, const uint8_t *data, uint32_t len);
