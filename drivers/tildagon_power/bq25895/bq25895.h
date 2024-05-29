
#ifndef BQ25895_H
#define BQ25895_H

#include <stdint.h>
#include "tildagon_i2c.h"

typedef enum
{
    BQ_NOTCHARGING  = 0x00,
    BQ_PRECHARGING  = 0x08,
    BQ_FASTCHARGING = 0x10,
    BQ_TERMINATED   = 0x18
} bq_charge_status_t;

typedef enum
{
    BQ_FAULT_NONE    = 0x00,
    BQ_FAULT_INPUT   = 0x04,
    BQ_FAULT_THERMAL = 0x08,
    BQ_FAULT_TIMER   = 0x0C,
} bq_charge_fault_t;

#define BQ_CHARGE_STAT_MASK   (uint8_t)0x18U
#define BQ_FAULT_BOOST_MASK   (uint8_t)0x08U
#define BQ_FAULT_CHARGE_MASK  (uint8_t)0x30U
#define BQ_FAULT_BATTERY_MASK (uint8_t)0x40U

typedef struct
{
    float vbus;
    float vsys;
    float vbat;
    float ichrg;
    uint8_t fault;
    uint8_t status;
    tildagon_mux_i2c_obj_t* mux_port;
} bq_state_t;

/**
 * @brief initialise the bq25895
 * @details reset then setup 500mA Iin limit, boost disabled, charging enabled,
 * ADC at 1Hz, disable unused features and disable watchdog to reduce interruptions
 * @param state pmic object
 */
extern void bq_init( bq_state_t* state );
/**
 * @brief Put the converter into High impedance mode on the input to prevent 
 * current draw or take it out of HiZ mode
 * @param state pmic object
 * @param enable uint8_t if > 0 enable the high impedance mode, if 0 disable 
 * the high impedance mode
 */
extern void bq_enable_HiZ_input( bq_state_t* state, uint8_t enable );
/**
 * @brief Control the boost output
 * @param state pmic object
 * @param enable uint8_t if > 0 enable boost converter
 * if 0 disable the boost converter
 */
extern void bq_enable_boost( bq_state_t* state, uint8_t enable );
/**
 * @brief Disconnect the battery from the IC
 * @param state pmic object
 */
extern void bq_disconnect_battery( bq_state_t* state );
/**
 * @brief Set the Input current limit
 * @param state pmic object
 * @param limit float Limit in mA, range 100-3250mA resolution 50mA
 */
extern void bq_set_input_current_limit( bq_state_t* state, float limit );
/**
 * @brief update the status
 * @param state pmic object
*/
extern void bq_update_state( bq_state_t* state );

#endif /* BQ25895_H */
