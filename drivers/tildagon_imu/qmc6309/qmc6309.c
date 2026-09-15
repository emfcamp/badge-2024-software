#include "tildagon_i2c_mpless.h"
#include "tildagon_i2c_manager.h"

#include "qmc6309.h"

#define ADDRESS 0x7CU
#define DATA_OUTPUT_REG 0x01U
#define CTRL_REG1 0x0AU
#define CTRL_REG2 0x0BU

static int8_t job_handle = -1;

int qmc6309_init( void )
{
    if ( job_handle >= 0 )
    {
        return job_handle;
    }

    /* continuous sampling, oversample 8, level 1 filter and 100 Hz, 8 gauss range */
    uint8_t config[3] = { 0x03U, 0x38U };
    if ( tildagon_i2c_reg_write( TILDAGON_TOP_I2C_PORT, ADDRESS, CTRL_REG1,
                                 config, 2 ) != ESP_OK )
    {
        return -1;
    }

    const tildagon_i2c_mgr_step_t steps[] = {
        {
            .type = TILDAGON_I2C_MGR_STEP_READ,
            .a = DATA_OUTPUT_REG,
            .b = 6,
        },
    };

    job_handle = (int8_t)tildagon_i2c_mgr_register_steps(
        TILDAGON_TOP_I2C_PORT, ADDRESS, steps, 1,
        TILDAGON_I2C_MGR_PERIOD_OFF, true );
    return job_handle;
}

void qmc6309_read( float* x, float*y, float*z )
{
    uint8_t buffer[6];
    if ( job_handle < 0 ||
         tildagon_i2c_mgr_read_into( job_handle, buffer, sizeof(buffer) ) < 0 )
    {
        *x = 0.0F;
        *y = 0.0F;
        *z = 0.0F;
        return;
    }

    *x = ((float)((int16_t)(buffer[2] + ((uint16_t)buffer[3] << 8)))) / 4095.0F;
    *y = -((float)((int16_t)(buffer[0] + ((uint16_t)buffer[1] << 8)))) / 4095.0F;
    *z = ((float)((int16_t)(buffer[4] + ((uint16_t)buffer[5] << 8)))) / 4095.0F;
}
