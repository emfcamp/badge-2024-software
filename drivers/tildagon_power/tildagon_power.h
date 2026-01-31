
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

typedef enum
{
    DISABLED,
    UNATTACHED,
    ATTACHED,
    MAX_STATES
} attach_machine_state_t;

typedef enum
{
    NOT_STARTED        = 0x00,
    WAITING            = 0x01,
    LANYARD            = 0x02,
} pd_machine_state_t;

extern bq_state_t pmic;
extern usb_state_t usb_in;
extern usb_state_t usb_out;
extern uint16_t input_current_limit;
extern attach_machine_state_t device_attach_state;
extern attach_machine_state_t host_attach_state;
extern pd_machine_state_t device_pd_state;
extern pd_machine_state_t host_pd_state;
extern bool badge_as_device;
extern bool badge_as_host;
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
