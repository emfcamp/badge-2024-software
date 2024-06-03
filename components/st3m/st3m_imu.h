#pragma once

#include "esp_err.h"

#include <stdbool.h>
#include <stdint.h>

void st3m_imu_init(void);

void st3m_imu_read_acc_mps(float *x, float *y, float *z);
void st3m_imu_read_gyro_dps(float *x, float *y, float *z);
void st3m_imu_read_pressure(float *pressure, float *temperature);
void st3m_imu_read_steps(uint32_t *steps);
