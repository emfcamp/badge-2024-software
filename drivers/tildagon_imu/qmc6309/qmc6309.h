#ifndef QMC6309_H
#define QMC6309_H

/* Initializes the device and registers its high-priority i2c manager job.
 * Returns the i2c manager handle, or -1 on failure. */
extern int qmc6309_init( void );

extern void qmc6309_read( float* x, float*y, float*z );

#endif
