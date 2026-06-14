#include "tildagon_i2c_mpless.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#include "qmc6309.h"

#define ADDRESS 0x7CU
#define DATA_OUTPUT_REG 0x01U
#define CTRL_REG1 0x0AU
#define CTRL_REG2 0x0BU
static SemaphoreHandle_t _mu;
#define LOCK xSemaphoreTake(_mu, portMAX_DELAY)
#define UNLOCK xSemaphoreGive(_mu)

static float qmc_x = 0.0F;
static float qmc_y = 0.0F;
static float qmc_z = 0.0F;

esp_err_t qmc6309_init( void )
{
    _mu = xSemaphoreCreateMutex();
    /* continuous sampling, oversample 8, level 1 filter and 100 Hz, 8 gauss range */
    uint8_t config[3] = { 0x03U, 0x38U };
    return tildagon_i2c_reg_write(TILDAGON_TOP_I2C_PORT, ADDRESS, CTRL_REG1, config, 2);

}

void qmc6309_update( void ) 
{
    uint8_t buffer[6] = { 0U };
    if ( tildagon_i2c_reg_read( TILDAGON_TOP_I2C_PORT, ADDRESS, DATA_OUTPUT_REG, buffer, 6U ) == ESP_OK )
    {
        LOCK;
        qmc_x = ((float)((int16_t)(buffer[2] + ((uint16_t)buffer[3] << 8))))/4095.0F;
        qmc_y = -((float)((int16_t)(buffer[0] + ((uint16_t)buffer[1] << 8))))/4095.0F;
        qmc_z = ((float)((int16_t)(buffer[4] + ((uint16_t)buffer[5] << 8))))/4095.0F;
        UNLOCK;
    }    
}

void qmc6309_read( float* x, float*y, float*z )
{
    LOCK;
    *x = qmc_x;
    *y = qmc_y;
    *z = qmc_z;
    UNLOCK;
}
