/*
    BQ25895 power management ic driver in c

The driver supports basic read write access with some helpers and setup

*/

#include "bq25895.h"

typedef struct
{
    uint8_t regaddr;
    uint8_t mask;
    uint8_t position;
} bq_register_t;

typedef struct
{
    uint8_t regaddr;
    uint8_t mask;
    uint8_t position;
    float scaling;
    float offset;
} scaled_register_t;

#define ADDRESS 0x6A
#define READ ( MP_MACHINE_I2C_FLAG_WRITE1 | MP_MACHINE_I2C_FLAG_READ | MP_MACHINE_I2C_FLAG_STOP )
#define WRITE MP_MACHINE_I2C_FLAG_STOP

static const scaled_register_t input_Ilim     = { 0x00U, 0x3FU, 0U, 50.0F, 100.0F };
static const bq_register_t     Ilim_pin       = { 0x00U, 0x40U, 6U };
static const bq_register_t     enable_HiZ     = { 0x00U, 0x80U, 7U };
static const bq_register_t     otg_boost      = { 0x03U, 0x20U, 5U };
static const bq_register_t     batfet_disable = { 0x09U, 0x20U, 5U };
static const bq_register_t     register_reset = { 0x14U, 0x80U, 7U };

static void write_bits( bq_state_t* state, bq_register_t reg, uint8_t value );
static void write_scaled( bq_state_t* state, scaled_register_t scaledregister, float value );

/**
 * @brief initialise the bq25895
 * @details reset then setup 500mA Iin limit, boost disabled, charging enabled,
 * ADC at 1Hz, disable unused features and disable watchdog to reduce interruptions
 * charge current limit to be 0.85C for the 1800mAh and 0.77C for 2000mAh batteries
 * termination and precharge current to 64mA. min Vsys to 3.0V
 * @param state pmic object
 */
void bq_init( bq_state_t* state )
{
    write_bits( state, register_reset, 1 );
    uint8_t write_buffer[5] = { 0x02, 0x60, 0x10, 0x18, 0x00 };
    mp_machine_i2c_buf_t buffer = { .len = 5, .buf = write_buffer };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
    write_buffer[0] = 0x07;
    write_buffer[1] = 0x8C;
    buffer.len = 2;
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
}

/**
 * @brief Put the converter into High impedance mode on the input to prevent 
 * current draw or take it out of HiZ mode
 * @param state pmic object
 * @param enable uint8_t if > 0 enable the high impedance mode, if 0 disable 
 * the high impedance mode
 */
void bq_enable_HiZ_input( bq_state_t* state,uint8_t enable )
{
    if (enable > 1)
    {
        enable = 1;
    }
    write_bits( state, enable_HiZ, enable );
}

/**
 * @brief Control the boost output
 * @param state pmic object
 * @param enable uint8_t if > 0 enable boost converter
 * if 0 disable the boost converter
 */
void bq_enable_boost( bq_state_t* state, uint8_t enable )
{
    if (enable > 1)
    {
        enable = 1;
    }
    write_bits( state, otg_boost, enable );
}

/**
 * @brief Disconnect the battery from the IC
 * @param state pmic object
 */
void bq_disconnect_battery( bq_state_t* state )
{
    write_bits( state, batfet_disable, 1 );
}

/**
 * @brief Set the Input current limit
 * @param state pmic object
 * @param limit float Limit in mA, range 100-3250mA resolution 50mA
 */
void bq_set_input_current_limit( bq_state_t* state, float limit )
{
    write_scaled( state, input_Ilim, limit );
    if (limit > 1500.0F)
    {
        write_bits( state, Ilim_pin, 1 );
    }
    else
    {
        write_bits( state, Ilim_pin, 0 );
    }
}

/**
 * @brief update the status
 * @param state pmic object
*/
void bq_update_state( bq_state_t* state )
{
    uint8_t address = 0x0BU;
    uint8_t read_buffer[8];
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &address },
                                       { .len = 8, .buf = read_buffer } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
    state->status = read_buffer[0];
    state->fault = read_buffer[1];
    if ( ( read_buffer[3] & 0x7F ) == 0U )
    {
        state->vbat = 0.0F;
    }
    else
    {
        state->vbat = ((float)( read_buffer[3] & 0x7F) * 0.02F ) + 2.304F;
    }
    if ( ( read_buffer[4] & 0x7F ) == 0U )
    {
        state->vsys = 0.0F;
    }
    else
    {
        state->vsys = ((float)( read_buffer[4] & 0x7F) * 0.02F ) + 2.304F;
    }
    if ( ( read_buffer[6] & 0x7F) == 0U )
    {
        state->vbus = 0.0F;
    }
    else
    {
        state->vbus = ((float)( read_buffer[6] & 0x7F) * 0.10F ) + 2.600F;
    }
    state->ichrg = ((float)( read_buffer[7] & 0x7F) * 0.05F );
}

/**
 * @brief read modify write a single register entry
 * @param state pmic object
 * @param reg bq_register_t details of the register to read
 * @param value uint to convert to a register entry
 */
inline void write_bits( bq_state_t* state, bq_register_t reg, uint8_t value )
{
    uint8_t regVal = 0U;
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &reg.regaddr },
                                       { .len = 1, .buf = &regVal } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
    regVal = regVal & (~reg.mask);
    regVal = regVal | ( value << reg.position );
     uint8_t write_buffer[2] = { reg.regaddr, regVal };
    buffer[0].len = 2;
    buffer[0].buf = write_buffer;    
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, buffer, WRITE );
 }

/**
 * @brief read modify write a value from a register after applying scaling and offset.
 * @param state pmic object
 * @param scaledregister scaled_register_t details of the register to read
 * @param value float to convert to a register entry
 */
inline void write_scaled( bq_state_t* state, scaled_register_t scaledregister, float value )
{
    uint8_t regVal = 0;
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &scaledregister.regaddr },
                                       { .len = 1, .buf = &regVal } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
    regVal = regVal & (~scaledregister.mask);
    regVal |= ( (int)(( value - scaledregister.offset ) / scaledregister.scaling ) << scaledregister.position ) & scaledregister.mask;
    uint8_t write_buffer[2] = { scaledregister.regaddr, regVal };
    ((mp_machine_i2c_buf_t*)&buffer[0])->len = 2;
    ((mp_machine_i2c_buf_t*)&buffer[0])->buf = write_buffer;
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, buffer, WRITE );
}
