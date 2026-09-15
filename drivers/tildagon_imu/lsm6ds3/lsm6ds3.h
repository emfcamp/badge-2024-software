#ifndef TILDAGON_LSM6DS3_H
#define TILDAGON_LSM6DS3_H

#include <stdint.h>
#include "tildagon_imu.h"

extern int  lsm6ds3_init( tildagon_imu_state_t *state );
extern void lsm6ds3_task_acc_gyro( void );
extern void lsm6ds3_task_temperature( void );
extern void lsm6ds3_task_steps( void );
extern void lsm6ds3_read_acc_mps(float *x, float *y, float *z);
extern void lsm6ds3_read_gyro_dps(float *x, float *y, float *z);
extern void lsm6ds3_read_steps(uint32_t *steps);
extern void lsm6ds3_read_temperature(float *temperature);
extern int  lsm6ds3_write(uint8_t reg_addr, uint8_t *reg_data, uint8_t len );
extern int  lsm6ds3_read(uint8_t reg_addr, uint8_t *reg_data, uint8_t len );
extern int  lsm6ds3_set_period(uint16_t period_ms);

#endif /* TILDAGON_LSM6DS3_H */
