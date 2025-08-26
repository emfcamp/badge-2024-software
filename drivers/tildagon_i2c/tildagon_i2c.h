#ifndef _MICROPY_PY_TILDAGON_I2C
#define _MICROPY_PY_TILDAGON_I2C


#include "tca9548a.h"
#include "driver/i2c.h"
#include "extmod/modmachine.h"

#if CONFIG_IDF_TARGET_ESP32C3 || CONFIG_IDF_TARGET_ESP32S3
#define I2C_SCLK_FREQ XTAL_CLK_FREQ
#elif CONFIG_IDF_TARGET_ESP32 || CONFIG_IDF_TARGET_ESP32S2
#define I2C_SCLK_FREQ APB_CLK_FREQ
#else
#error "unsupported I2C for ESP32 SoC variant"
#endif

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


typedef struct _tildagon_mux_i2c_obj_t {
    mp_obj_base_t base;
    const tca9548a_i2c_mux_t *mux;
    tca9548a_i2c_port_t port;
} tildagon_mux_i2c_obj_t;

const tca9548a_i2c_mux_t *tildagon_get_i2c_mux();

tildagon_mux_i2c_obj_t *tildagon_get_mux_obj( uint8_t port );

void tildagon_i2c_init();

int tildagon_mux_i2c_transaction(tildagon_mux_i2c_obj_t *self_in, uint16_t addr, size_t n, mp_machine_i2c_buf_t *bufs, unsigned int flags);

#endif // _MICROPY_PY_TILDAGON_I2C
