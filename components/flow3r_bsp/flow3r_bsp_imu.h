#pragma once

#include "bmi2_defs.h"

#include "tildagon_i2c.h"

#include "esp_err.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    struct bmi2_dev bmi;
    uint8_t bmi_dev_addr;
    int acc_range;   // accelerometer range in g.
    int gyro_range;  // gyroscope range in degrees per second.
} flow3r_bsp_imu_t;

// Init the IMU with default settings
//
// Configures the IMU to:
// Accelerometer: 100 Hz sample rate, 2 g range
// Gyroscope: 100 Hz sample rate, 200 dps range
// Pressure sensor: 50 Hz sample rate
esp_err_t flow3r_bsp_imu_init(flow3r_bsp_imu_t *imu);

// Update the IMU readings by reading data from the I2C bus.
//
// This directly calls the I2C bus and waits until the bus is available (max 1
// second).
// Returns ESP_FAIL if the sensor could not be read (e.g. I2C unavailable).
esp_err_t flow3r_bsp_imu_update(flow3r_bsp_imu_t *imu);

// Get an accelerometer reading.
//
// Returns ESP_ERR_NOT_FOUND if there is no new reading available.
// Return values are raw data from the BMI270.
// Use imu->acc_range and imu->bmi.resolution for interpretation.
esp_err_t flow3r_bsp_imu_read_acc(flow3r_bsp_imu_t *imu, int *x, int *y,
                                  int *z);

// Get aa converted accelerometer reading.
//
// Returns ESP_ERR_NOT_FOUND if there is no new reading available.
// Return values in m/s**2.
esp_err_t flow3r_bsp_imu_read_acc_mps(flow3r_bsp_imu_t *imu, float *x, float *y,
                                      float *z);

// Get a gyroscope reading.
//
// Returns ESP_ERR_NOT_FOUND if there is no new reading available.
// Return values are raw data from the BMI270.
// Use imu->gyro_range and imu->bmi.resolution for interpretation.
esp_err_t flow3r_bsp_imu_read_gyro(flow3r_bsp_imu_t *imu, int *x, int *y,
                                   int *z);

// Get converted gyroscope reading.
//
// Returns ESP_ERR_NOT_FOUND if there is no new reading available.
// Return values in deg/s.
esp_err_t flow3r_bsp_imu_read_gyro_dps(flow3r_bsp_imu_t *imu, float *x,
                                       float *y, float *z);

// Get step count.
//
// Returns ESP_ERR_NOT_FOUND if there is no new reading available.
// Returns ESP_FAIL if the sensor could not be read (e.g. I2C unavailable).
// Retrurns the number of steps counted.
esp_err_t flow3r_bsp_imu_read_steps(flow3r_bsp_imu_t *imu, uint32_t *steps);

// Get temperature
//
// Returns ESP_FAIL if the sensor could not be read (e.g. I2C unavailable).
// Returns temperature in 'C
esp_err_t flow3r_bsp_imu_read_temperature(flow3r_bsp_imu_t *imu, float *temperature);

// i2c write
// writes buffer to register address
// Returns bmi fault code
BMI2_INTF_RETURN_TYPE bmi2_i2c_write(uint8_t reg_addr,const uint8_t *reg_data,
                                            uint32_t len, void *intf_ptr);
// i2c read
// reads buffer from register address
// Returns bmi fault code                                            
BMI2_INTF_RETURN_TYPE bmi2_i2c_read(uint8_t reg_addr, uint8_t *reg_data,
                                           uint32_t len, void *intf_ptr);