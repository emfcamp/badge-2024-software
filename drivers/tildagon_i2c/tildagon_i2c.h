#ifndef _MICROPY_PY_TILDAGON_I2C
#define _MICROPY_PY_TILDAGON_I2C

#if CONFIG_IDF_TARGET_ESP32C3 || CONFIG_IDF_TARGET_ESP32S3
#define I2C_SCLK_FREQ XTAL_CLK_FREQ
#elif CONFIG_IDF_TARGET_ESP32 || CONFIG_IDF_TARGET_ESP32S2
#define I2C_SCLK_FREQ APB_CLK_FREQ
#else
#error "unsupported I2C for ESP32 SoC variant"
#endif

#define TILDAGON_HOST_I2C_SDA (8)
#define TILDAGON_HOST_I2C_SCL (9)
#define TILDAGON_HOST_I2C_FREQ (400000)
#define TILDAGON_HOST_I2C_PORT (0)
#define TILDAGON_HOST_I2C_TIMEOUT (50000)

const tca9548a_i2c_mux_t *tildagon_get_i2c_mux();

void tildagon_i2c_init();


#endif // _MICROPY_PY_TILDAGON_I2C