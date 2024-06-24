
#ifndef TILDAGON_POWER_H
#define TILDAGON_POWER_H


#include <stdint.h>
#include <stdbool.h>
#include "bq25895/bq25895.h"
#include "fusb302b/fusb302b_pd.h"
#include "fusb302b/fusb302b.h"

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
