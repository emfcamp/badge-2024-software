/*
FUSB302 Programmable USB Type-C Controller w/PD driver in MicroPython. 

The driver supports basic read write access with some helpers

*/
#include "fusb302b.h"
#include "fusb302b_pd.h"

typedef struct
{
    uint8_t regaddr;
    uint8_t mask;
    uint8_t position;
} fusb_register_t;


#define ADDRESS 0x22
#define READ ( MP_MACHINE_I2C_FLAG_WRITE1 | MP_MACHINE_I2C_FLAG_READ | MP_MACHINE_I2C_FLAG_STOP )
#define WRITE MP_MACHINE_I2C_FLAG_STOP
static const fusb_register_t select_cc              = { 0x02U, 0x0CU, 2U };
static const fusb_register_t enable_bmc             = { 0x03U, 0x03U, 0U };
static const fusb_register_t auto_crc               = { 0x03U, 0x04U, 2U };
static const fusb_register_t tx_flush               = { 0x06U, 0x40U, 6U };
static const fusb_register_t rx_flush               = { 0x07U, 0x04U, 2U };
static const fusb_register_t mask_bc_level          = { 0x0AU, 0x01U, 0U };
static const fusb_register_t mask_comparator_change = { 0x0AU, 0x20U, 5U };
static const fusb_register_t enable_oscillator      = { 0x0BU, 0x01U, 0U };
static const fusb_register_t register_reset         = { 0x0CU, 0x01U, 0U };
static const fusb_register_t pd_reset               = { 0x0CU, 0x02U, 1U };
static const fusb_register_t mask_hardreset_int     = { 0x0EU, 0x01U, 0U };   
static const fusb_register_t mask_softreset_int     = { 0x0EU, 0x02U, 1U }; 
static const fusb_register_t mask_tx_sent_int       = { 0x0EU, 0x04U, 2U };     
static const fusb_register_t mask_retry_fail_int    = { 0x0EU, 0x10U, 4U };
static const fusb_register_t mask_toggle_done_int   = { 0x0EU, 0x40U, 6U };
static const fusb_register_t mask_good_crc_sent_int = { 0x0FU, 0x01U, 0U };
static const fusb_register_t rx_fifo_empty          = { 0x41U, 0x20U, 5U };
    
static void power_up( fusb_state_t* state );
static uint8_t read_bits( fusb_state_t* state, fusb_register_t reg );
static void write_bits( fusb_state_t* state, fusb_register_t reg, uint8_t value );

/** 
 * @brief Initialise the fusb302 to a device 
 * @details reset the device then set comparator threshold to 2.226V, enable Vbus measurement,
 * flush buffers, enable interrupts, 3 retries and Vbus, BC level and good crc interrupts, enable toggle
 * @param state the port object
 */
void fusb_setup_device( fusb_state_t* state )
{
    write_bits( state, register_reset, 1 ); 
    power_up(state);
    uint8_t write_buffer[13] = { 0x04, 0x3E, 0x60, 0x44, 0x04, 0xA5, 0x07, 0x7F, 0x07, 0x00, 0x0F, 0x3F, 0x00 };
    mp_machine_i2c_buf_t buffer = { .len = 13, .buf = write_buffer };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
    state->host = 0U;
    state->input_current_limit = 500U;
    state->cc_select = 0U;
}

/**
 * @brief Initialise the fusb302 to a host
 * @details reset then setup pull ups, data roles, cc measurement level, enable toggle
 * and toggle interrupt, 1.5A current limit, 3 auto retries and flush buffers
 * @param state the port object
 */
void fusb_setup_host( fusb_state_t* state )
{
    write_bits( state, register_reset, 1 );
    power_up(state);
    uint8_t write_buffer[15] = { 0x02, 0xC0, 0xB0, 0x25, 0x60, 0x48, 0x04, 0xA7, 0x07, 0xFF, 0x07, 0x00, 0x0F, 0xB0, 0x01 };
    mp_machine_i2c_buf_t buffer = { .len = 15, .buf = write_buffer };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
    state->cc_select = 0U;
    state->host = 1U;
}

/**
 * @brief set the measurement to a cc line
 * @param state the port object
 * @param cc_select the pin to measure on
 */
void fusb_set_cc( fusb_state_t* state, uint8_t cc_select )
{
    write_bits( state, select_cc, cc_select );
}

/**
 * @brief disable toggle
 * @param state the port object
 */
void fusb_stop_toggle( fusb_state_t* state )
{
    uint8_t write_buffer[2] = { 0x08, 0x00 };
    mp_machine_i2c_buf_t buffer = { .len = 2, .buf = write_buffer };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
}

/**
 * @brief status read from the device
 * @param state the port object
 */
void fusb_get_status( fusb_state_t* state )
{
    uint8_t read_buffer[2];
    uint8_t address = 0x40;
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &address },
                                       { .len = 2, .buf = read_buffer } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
    state->status = read_buffer[0] | ( (uint16_t)read_buffer[1] << 8 );
}

/**
 * @brief statusa read from the device
 * @param state the port object
 */
void fusb_get_statusa( fusb_state_t* state )
{
    uint8_t read_buffer[2];
    uint8_t address = 0x3C;
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &address },
                                       { .len = 2, .buf = read_buffer } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
    state->statusa =  read_buffer[0] | ( (uint16_t)read_buffer[1] << 8 );
}

/**
 * @brief read interrupt a and b registers
 * @param state the port object
 */
uint16_t fusb_get_interruptab( fusb_state_t* state )
{
    uint8_t read_buffer[2];
    uint8_t address = 0x3E;
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &address },
                                       { .len = 2, .buf = read_buffer } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
    return read_buffer[0] | ( (uint16_t)read_buffer[1] << 8 );
}

/**
 * @brief read interrupt register
 * @param state the port object
 */
uint8_t fusb_get_interrupt( fusb_state_t* state )
{
    uint8_t read_buffer;
    uint8_t address = 0x42;
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &address },
                                       { .len = 1, .buf = &read_buffer } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
    return read_buffer;
}

/**
 * @brief setup the PD to send the good CRC packet automatically
 * @param state the port object
 */
void fusb_auto_good_crc ( fusb_state_t* state )
{
    write_bits( state, auto_crc, 1 );
}

/**
 * @brief flush both the rx and tx buffers
 * @param state the port object
 */
void fusb_flush_buffers( fusb_state_t* state )
{
    write_bits( state, tx_flush, 1 );
    write_bits( state, rx_flush, 1 );
}

/**
 * @brief mask toggle interrupt
 * @param state the port object
 * @param value of mask
 */
void fusb_mask_interrupt_toggle( fusb_state_t* state, uint8_t value )
{
    write_bits( state, mask_toggle_done_int, value );
}

/**
 * @brief mask comparator interrupt
 * @param state the port object
 * @param value of mask
 */
void fusb_mask_interrupt_comp( fusb_state_t* state, uint8_t value )
{
    write_bits( state, mask_comparator_change, value );
}

/**
 * @brief mask BC level interrupt
 * @param state the port object
 * @param value of mask
 */
void fusb_mask_interrupt_bclevel( fusb_state_t* state, uint8_t value )
{
    write_bits( state, mask_bc_level, value );
}

/**
 * @brief mask PD good CRC interrupt
 * @param state the port object
 * @param value of mask
 */
void fusb_mask_interrupt_gdcrc( fusb_state_t* state, uint8_t value )
{
    write_bits( state, mask_good_crc_sent_int, value );
}

/**
 * @brief mask PD soft reset interrupt
 * @param state the port object
 * @param value of mask
 */
void fusb_mask_interrupt_softreset( fusb_state_t* state, uint8_t value )
{
    write_bits( state, mask_softreset_int, value );
}

/**
 * @brief mask PD hard reset interrupt
 * @param state the port object
 * @param value of mask
 */
void fusb_mask_interrupt_hardreset( fusb_state_t* state, uint8_t value )
{
    write_bits( state, mask_hardreset_int, value );
}

/**
 * @brief mask PD retry failure interrupt
 * @param state the port object
 * @param value of mask
 */
void fusb_mask_interrupt_retryfail( fusb_state_t* state, uint8_t value )
{
    write_bits( state, mask_retry_fail_int, value );    
}

/**
 * @brief mask PD tx sent got a good crc interrupt
 * @param state the port object
 * @param value of mask
 */
void fusb_mask_interrupt_txsent( fusb_state_t* state, uint8_t value )
{
    write_bits( state, mask_tx_sent_int, value );  
}

/**
 *  @brief enable or disable comms based on cc_select
 * @param state the port object
 */       
void fusb_setup_pd( fusb_state_t* state )
{
    if ( state->cc_select )
    {
        uint8_t write_buffer[2] = { 0x08, 0x04 };
        mp_machine_i2c_buf_t buffer = { .len = 2, .buf = write_buffer };
        tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
        write_buffer[0] = mask_good_crc_sent_int.regaddr;
        write_buffer[1] = 0x00;
        tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
        
        write_bits( state, rx_flush, 1 );
        uint8_t data = 0x20;
        if ( state->cc_select == 1 )
        {
            data |= 0x01;
        }
        else
        {
            data |= 0x02;
        }
        if ( state->host == 0 )
        {
            data |= 0x84;
        }
        else
        {
            data |= 0x04;
        }
        write_buffer[0] = enable_bmc.regaddr;
        write_buffer[1] = data;
        tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
        write_bits( state, tx_flush, 1 );
        write_bits( state, rx_flush, 1 );
        write_buffer[0] = 0x0B;
        write_buffer[1] = 0x0F;
        tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
        write_buffer[0] = pd_reset.regaddr;
        write_buffer[1] = 0x02;
        tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
    }
    else
    {
        write_bits( state, auto_crc, 0 );
        write_bits( state, mask_good_crc_sent_int, 1 );
        write_bits( state, enable_bmc, 0 );
    }
}    

/**
 * @brief are bytes available 
 * @param state the port object
 */
uint8_t fusb_rx_empty( fusb_state_t* state )
{
    return read_bits( state, rx_fifo_empty );
}        

/**
 * @brief get the contents of the rx fifo
 * @param state the port object
 * @param rx_buffer buffer to return the data of size length
 * @param length amount of data
 */
void fusb_get_fifo(fusb_state_t* state, uint8_t* rx_buffer, uint8_t length )
{
    uint8_t address = 0x43;
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &address },
                                       { .len = length, .buf = rx_buffer } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
}

/**
 * @brief send a message to the tx fifo of up to PD_MAX_TX_MSG_SIZE bytes
 * @param state the port object
 * @param message buffer to send, must be prefixed with TX_FIFO_ADDRESS.
 * @param length amount of data
 */
void fusb_send( fusb_state_t* state, uint8_t* message, uint8_t length )
{ 
    mp_machine_i2c_buf_t buffer = { .len = length, .buf = message };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );    
}

/**
 * @brief Turn on parts of the fusb hardware 
 * @param state the port object
 */
void power_up( fusb_state_t* state )
{
    /* 
        bit 0: Bandgap and wake circuit.
        bit 1: Receiver powered and current references for Measure block
        bit 2: Measure block powered.
        bit 3: Enable internal oscillator.
    */
    uint8_t write_buffer[2] = { enable_oscillator.regaddr, 0x07 };
    mp_machine_i2c_buf_t buffer = { .len = 2, .buf = write_buffer };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 1, &buffer, WRITE );
}

/**
 * @brief Returns a value from the selected bits of a register
 * @param state the port object
 * @param reg fusb_register_t details of the register to read
 * @return the value of the register
 */
uint8_t read_bits( fusb_state_t* state, fusb_register_t reg )
{
    uint8_t regVal = 0;
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &reg.regaddr },
                                       { .len = 1, .buf = &regVal } };
    tildagon_mux_i2c_transaction( state->mux_port, ADDRESS, 2, buffer, READ );
    return ( ( regVal & reg.mask) >> reg.position ) ;
}

/**
 * @brief read modify write a single register entry
 * @param state the port object
 * @param reg fusb_register_t details of the register to read
 * @param value uint to convert to a register entry
 */
void write_bits( fusb_state_t* state, fusb_register_t reg, uint8_t value )
{
    uint8_t regVal = 0;
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
