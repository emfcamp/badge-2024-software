#include "lsm6ds3.h"

#include "tildagon_i2c.h"
#include "esp_err.h"
#include "freertos/semphr.h"

/* Accelerometer and gyroscope control registers */
#define CTRL1_XL                 0x10
#define CTRL3_C                  0x12
#define CTRL10_C                 0x19
/* Temperature output data registers */
#define OUT_TEMP_L               0x20
/* Gyroscope output data registers */
#define OUT_GYRO_X_L            0x22
#define OUT_GYRO_Y_L            0x24
#define OUT_GYRO_Z_L            0x26
/* Accelerometer output data registers */
#define OUT_ACC_X_L             0x28
#define OUT_ACC_Y_L             0x2A
#define OUT_ACC_Z_L             0x2C
/* Step counter output registers */
#define STEP_COUNTER_L           0x4B

static esp_err_t reset( void );

#define ADDRESS 0x6B
#define READ ( MP_MACHINE_I2C_FLAG_WRITE1 | MP_MACHINE_I2C_FLAG_READ | MP_MACHINE_I2C_FLAG_STOP )
#define WRITE MP_MACHINE_I2C_FLAG_STOP

static tildagon_imu_state_t *imu_state = NULL;
tildagon_mux_i2c_obj_t* mux_port;

static SemaphoreHandle_t _mu;

#define LOCK xSemaphoreTake(_mu, portMAX_DELAY)
#define UNLOCK xSemaphoreGive(_mu)

/**
 * @brief initialise lsm6ds3
 * @details setup the lsm6ds3 2g accel and 2000dps gyro at 26Hz
 * @return esp_err_t expect ESP_OK or ESP_FAIL
 */
esp_err_t lsm6ds3_init( tildagon_imu_state_t *state )
{
    imu_state = state;
    if ( imu_state == NULL )
    {
        return ESP_FAIL;
    }

    _mu = xSemaphoreCreateMutex();
    assert(_mu != NULL);

    esp_err_t err = ESP_FAIL;
    mux_port = tildagon_get_mux_obj( TILDAGON_SYS_I2C_PORT );
    if (reset() >= 0)
    {
        /* 2 g accel and 2000 dps gyro at 26Hz */
        uint8_t write_buffer[3] = { CTRL1_XL, 0x21, 0x2C };
        mp_machine_i2c_buf_t buffer = { .len = 3, .buf = write_buffer };
        tildagon_mux_i2c_transaction( mux_port, ADDRESS, 1, &buffer, WRITE );
        /* enable step count */
        write_buffer[0] = CTRL10_C;
        /* PEDO_EN and FUNC_EN */
        write_buffer[1] = 0x14;
        tildagon_mux_i2c_transaction( mux_port, ADDRESS, 1, &buffer, WRITE );
        err = ESP_OK;
    }
    return err;
}

/**
 * @brief get accelerometer data
 * @param x pointer for x axis data
 * @param y pointer for y axis data
 * @param z pointer for z axis data
 */
void lsm6ds3_read_acc_mps(float *x, float *y, float *z)
{
    if ( imu_state == NULL )
    {
        *x = 0.0F;
        *y = 0.0F;
        *z = 0.0F;
        return;
    }

    LOCK;
    *x = imu_state->acc_x;
    *y = imu_state->acc_y;
    *z = imu_state->acc_z;
    UNLOCK;
}

/**
 * @brief get Gyroscope data
 * @param x pointer for x axis data
 * @param y pointer for y axis data
 * @param z pointer for z axis data
 */
void lsm6ds3_read_gyro_dps(float *x, float *y, float *z)
{
    if ( imu_state == NULL )
    {
        *x = 0.0F;
        *y = 0.0F;
        *z = 0.0F;
        return;
    }

    LOCK;
    *x = imu_state->gyro_x;
    *y = imu_state->gyro_y;
    *z = imu_state->gyro_z;
    UNLOCK;
}

/**
 * @brief get step count
 * @param steps pointer for data
 */
void lsm6ds3_read_steps(uint32_t *steps)
{
    if ( imu_state == NULL )
    {
        *steps = 0U;
        return;
    }

    LOCK;
    *steps = imu_state->steps;
    imu_state->steps = 0U;
    UNLOCK;
}

/**
 * @brief get temperature
 * @param temperature pointer for data
 */
void lsm6ds3_read_temperature(float *temperature)
{
    if ( imu_state == NULL )
    {
        *temperature = 0.0F;
        return;
    }

    LOCK;
    *temperature = imu_state->temperature;
    UNLOCK;
}

/**
 * @brief raw i2c write access
 * @param reg_addr address to write
 * @param reg_data data
 * @param len length of data
 */
int lsm6ds3_write(uint8_t reg_addr, uint8_t *reg_data, uint8_t len )
{
    if ( len == 0U )
    {
        return 0;
    }

    return tildagon_i2c_reg_write( TILDAGON_SYS_I2C_PORT, ADDRESS,
                                   reg_addr, reg_data, len );
}

/**
 * @brief raw i2c read access
 * @param reg_addr address to write
 * @param reg_data data
 * @param len length of data
 */
int lsm6ds3_read(uint8_t reg_addr, uint8_t *reg_data, uint8_t len )
{
    return tildagon_i2c_reg_read( TILDAGON_SYS_I2C_PORT, ADDRESS,
                                  reg_addr, reg_data, len );
}

int lsm6ds3_set_period(uint16_t period_ms)
{
    uint8_t config[2];
    int ret = lsm6ds3_read(CTRL1_XL, config, sizeof(config));
    if (ret < 0)
    {
        return ret;
    }

    uint8_t odr = 0x20; /* 26Hz */
    if (period_ms <= 10)
    {
        odr = 0x40; /* 104Hz */
    }
    else if (period_ms <= 20)
    {
        odr = 0x30; /* 52Hz */
    }

    config[0] = (config[0] & 0x0F) | odr;
    config[1] = (config[1] & 0x0F) | odr;
    return lsm6ds3_write(CTRL1_XL, config, sizeof(config));
}

/**
 * @brief update task acc/gyro
 */
void lsm6ds3_task_acc_gyro( void )
{
    /* Read the gyro and accelerometer registers as a contiguous 12-byte block.
     * The first byte is the low byte of OUT_GYRO_X_L; the 12 bytes cover
     * OUT_GYRO_X_L..OUT_ACC_Z_H and nothing else. */
    uint8_t reg = OUT_GYRO_X_L;
    uint8_t read_buffer[12] = { 0U };
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &reg },
                                       { .len = 12, .buf = read_buffer } };
    esp_err_t ret = tildagon_mux_i2c_transaction( mux_port, ADDRESS, 2, buffer, READ );
    if (ret >= 0)
    {
        if ( imu_state == NULL )
        {
            return;
        }

        LOCK;
        const float gyroscaling = (2000.0F / 32768.0F);
        imu_state->gyro_x = ((float)((int16_t)( read_buffer[0] | ((uint16_t)read_buffer[1] << 8) ))) * gyroscaling;
        imu_state->gyro_y = ((float)((int16_t)( read_buffer[2] | ((uint16_t)read_buffer[3] << 8) ))) * gyroscaling;
        imu_state->gyro_z = ((float)((int16_t)( read_buffer[4] | ((uint16_t)read_buffer[5] << 8) ))) * gyroscaling;
        /* 2g fsd, 1g = 9.80665m/s */
        const float accelscaling = (2.0F * 9.80665F) / 32768.0F;
        imu_state->acc_x = ((float)((int16_t)( read_buffer[6] | ((uint16_t)read_buffer[7] << 8) ))) * accelscaling;
        imu_state->acc_y = ((float)((int16_t)( read_buffer[8] | ((uint16_t)read_buffer[9] << 8) ))) * accelscaling;
        imu_state->acc_z = ((float)((int16_t)( read_buffer[10] | ((uint16_t)read_buffer[11] << 8) ))) * accelscaling;
        UNLOCK;
    }
}

/**
 * @brief update task temperature
 */
void lsm6ds3_task_temperature( void )
{
    uint8_t reg = OUT_TEMP_L;
    uint8_t read_buffer[2] = { 0U };
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &reg },
                                       { .len = 2, .buf = read_buffer } };
    esp_err_t ret = tildagon_mux_i2c_transaction( mux_port, ADDRESS, 2, buffer, READ );
    if (ret >= 0)
    {
        if ( imu_state == NULL )
        {
            return;
        }

        LOCK;
        imu_state->temperature = (((float)((int16_t)(read_buffer[0] | ((uint16_t)read_buffer[1] << 8)))) * 0.001953125F) + 23.0F;
        UNLOCK;
    }
}

/**
 * @brief update task steps
 */
void lsm6ds3_task_steps( void )
{
    uint8_t reg = STEP_COUNTER_L;
    uint8_t read_buffer[2] = { 0U };
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &reg },
                                       { .len = sizeof(read_buffer), .buf = read_buffer } };
    esp_err_t ret = tildagon_mux_i2c_transaction( mux_port, ADDRESS, 2, buffer, READ );
    if (ret >= 0)
    {
        if ( imu_state == NULL )
        {
            return;
        }

        LOCK;
        imu_state->steps += (uint16_t)read_buffer[0] | ((uint16_t)read_buffer[1] << 8);
        /* Reset the step count by reasserting the pedometer enable value. */
        uint8_t write_buffer[2] = { CTRL10_C, 0x14 };
        mp_machine_i2c_buf_t reset_buffer = { .len = 2, .buf = write_buffer };
        tildagon_mux_i2c_transaction( mux_port, ADDRESS, 1, &reset_buffer, WRITE );
        UNLOCK;
    }
}

/**
 * @brief reset
 * @details perform a software reset
 * @return esp_err_t
 */
esp_err_t reset()
{
    uint8_t write_buffer[2] = { CTRL3_C, 0x01 };
    mp_machine_i2c_buf_t buffer = { .len = 2, .buf = write_buffer };
    return tildagon_mux_i2c_transaction( mux_port, ADDRESS, 1, &buffer, WRITE );
}
