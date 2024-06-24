
#ifndef TILDAGON_POWER_H
#define TILDAGON_POWER_H


#include <stdint.h>
#include <stdbool.h>
#include "bq25895/bq25895.h"
#include "fusb302b/fusb302b_pd.h"
#include "fusb302b/fusb302b.h"

/* 
    minimum input voltage for step down at max (4A) load. 
    minimum input voltage = ( Rl(DCR) + Rdson ) * max current + output voltage
    (0.078ohms * 4.0A) + 3.3V = 3.6V 
    most users won't use 4A so badge will run lower than this so use 3.5V as minimum.
*/
#define VBATMAX 4.14F
#define VBATMIN 3.5F
#define IBAT_MAX 1.536F
#define IBAT_TERM 0.064F
typedef struct
{
    fusb_state_t fusb;
    pd_state_t pd;
} usb_state_t;

extern bq_state_t pmic;
extern usb_state_t usb_in;
extern usb_state_t usb_out;

/**
 * @brief initialise the badge power management task
 */
extern void tildagon_power_init( void );
/**
 * @brief add an interrupt event to the queue. intended to be called from an ISR
 */
extern void tildagon_power_interrupt_event ( void* param );
/**
 * @brief disconnect the battery to allow turn off on usb is disconnect
 */
extern void tildagon_power_off( void );
/**
 * @brief turn the 5V supply on or off
 */
extern void tildagon_power_enable_5v( bool enable );


#endif
