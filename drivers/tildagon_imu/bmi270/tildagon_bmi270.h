/*
 * Copyright (c) 2023 Bosch Sensortec GmbH. All rights reserved.
 *
 * This header is derived from the Bosch Sensortec BMI270 Sensor API reference
 * code and is kept in sync with the upstream Bosch version v2.86.1 used as the
 * implementation basis for the minimal Tildagon IMU driver.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 * 3. Neither the name of the copyright holder nor the names of its contributors
 *    may be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#ifndef TILDAGON_BMI270_H
#define TILDAGON_BMI270_H

#include <stdint.h>
#include "tildagon_imu.h"

extern int  bmi270_init( tildagon_imu_state_t *state );
extern void bmi270_task_acc_gyro( void );
extern void bmi270_task_temperature( void );
extern void bmi270_task_steps( void );
extern void bmi270_read_acc_mps(float *x, float *y, float *z);
extern void bmi270_read_gyro_dps(float *x, float *y, float *z);
extern void bmi270_read_steps(uint32_t *steps);
extern void bmi270_reset_steps( void );
extern void bmi270_read_temperature(float *temperature);
extern int  bmi270_write(uint8_t reg_addr, uint8_t *reg_data, uint8_t len );
extern int  bmi270_read(uint8_t reg_addr, uint8_t *reg_data, uint8_t len );
extern int  bmi270_set_period(uint16_t period_ms);

#endif /* TILDAGON_BMI270_H */
