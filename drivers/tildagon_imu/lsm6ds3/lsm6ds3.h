#ifndef LSM6DS3_H
#define LSM6DS3_H

#include <stdint.h>

extern int lsm6ds3_init( void );
extern void lsm6ds3_task(void *data);
extern void lsm6ds3_read_acc_mps(float *x, float *y, float *z);
extern void lsm6ds3_read_gyro_dps(float *x, float *y, float *z);
extern void lsm6ds3_read_steps(uint32_t *steps);
extern void lsm6ds3_read_temperature(float *temperature);
extern int  lsm6ds3_write(uint8_t reg_addr, uint8_t *reg_data, uint8_t len );
extern int  lsm6ds3_read(uint8_t reg_addr, uint8_t *reg_data, uint8_t len );
#endif /* LSM6DS3_H */