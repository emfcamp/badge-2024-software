#ifndef QMC6309_H
#define QMC6309_H

#include "esp_err.h"

esp_err_t qmc6309_init( void );

void qmc6309_update( void );

void qmc6309_read( float* x, float*y, float*z );

#endif