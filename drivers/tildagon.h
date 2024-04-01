#ifndef _TILDAGON_H
#define _TILDAGON_H

#include "tca9548a.h"

#define TILDAGON_HOST_I2C_SDA (8)
#define TILDAGON_HOST_I2C_SCL (9)
#define TILDAGON_HOST_I2C_FREQ (400000)
#define TILDAGON_HOST_I2C_PORT (0)
#define TILDAGON_HOST_I2C_TIMEOUT (50000)

const tca9548a_i2c_mux_t *tildagon_get_i2c_mux();


#endif // _TILDAGON_H