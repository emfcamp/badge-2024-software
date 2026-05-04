#pragma once

#include "esp_err.h"

#include <stdbool.h>
#include <stdint.h>

esp_err_t st3m_imu_init(void);

extern void st3m_imu_task(void *data);
extern void st3m_imu_read_acc_mps(float *x, float *y, float *z);
extern void st3m_imu_read_gyro_dps(float *x, float *y, float *z);
extern void st3m_imu_read_pressure(float *pressure, float *temperature);
extern void st3m_imu_read_steps(uint32_t *steps);
extern void st3m_imu_read_temperature(float *temperature);
extern int  st3m_imu_read(uint8_t reg_addr, uint8_t *reg_data, uint8_t len);
extern int  st3m_imu_write(uint8_t reg_addr, uint8_t *reg_data, uint8_t len);