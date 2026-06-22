#include "tildagon_i2c_mpless.h"
#include "cy8cmbrx.h"
#include <stdint.h>


#define READ ( MP_MACHINE_I2C_FLAG_WRITE1 | MP_MACHINE_I2C_FLAG_READ | MP_MACHINE_I2C_FLAG_STOP )
#define WRITE MP_MACHINE_I2C_FLAG_STOP

tildagon_mux_i2c_obj_t* cy8_mux_port;
uint16_t button_prev_status = 0U;
uint16_t prox_prev_status = 0U;

void send_command( uint8_t cmd );
static int write_bytes( tildagon_mux_i2c_obj_t* mux_port, uint8_t reg_adr, uint8_t* data, uint8_t length );

void cy8cmbrx_init( tildagon_mux_i2c_obj_t* new_port )
{
    cy8_mux_port = new_port;
}

cy8cmbrx_status_t cy8cmbrx_run( void )
{
    cy8cmbrx_status_t result = {0};
    /* read touch and prox current and latched status  */
    uint8_t raw_buf[6] = { 0U };
    /* check we have the device present */
    if( tildagon_i2c_reg_read(TILDAGON_TOP_I2C_PORT, CY8CMBRX_ADDRESS, CY8CMBRX_BUTTON_STAT_ADR, raw_buf, 6) == ESP_OK )
    {
        uint16_t button_state = ((uint16_t)raw_buf[1] << 8) +  raw_buf[0];
        uint16_t button_latch = ((uint16_t)raw_buf[3] << 8) +  raw_buf[2];
        uint8_t prox_state = raw_buf[4];
        uint8_t prox_latch = raw_buf[5];
        /* button detection */
        for( uint8_t i = 3U; i < 15U; i++ )
        {
            if ( ( button_latch & ( 1 << i ) ) && ( ( button_prev_status & ( 1 << i ) ) == 0U ) )
            {
                if ( ( button_state & ( 1 << i ) ) == 0U )
                {
                    result.buttons[i-3] = CY8CMBRX_PULSE;
                }
                else
                {
                    result.buttons[i-3] = CY8CMBRX_RISING_EDGE;
                }
            }
            else if ( ( button_prev_status & ( 1 << i ) ) && ( ( button_state & ( 1 << i ) ) == 0 ) )
            {
                result.buttons[i-3] = CY8CMBRX_FALLING_EDGE;
            }
        }
        button_prev_status = button_state;
        /* prox detection */
        for( uint8_t i = 0U; i < 2U; i++ )
        {
            if ( ( prox_latch & ( 1 << i ) ) && ( ( prox_prev_status & ( 1 << i ) ) == 0U ) )
            {
                if ( ( prox_state & ( 1 << i ) ) == 0U )
                {
                    result.prox[i] = CY8CMBRX_PULSE;
                }
                else
                {
                    result.prox[i] = CY8CMBRX_RISING_EDGE;
                }
            }
            else if ( ( prox_prev_status & ( 1 << i ) ) && ( ( prox_state & ( 1 << i ) ) == 0 ) )
            {
                result.prox[i] = CY8CMBRX_FALLING_EDGE;
            }
        }
        prox_prev_status = prox_state;
    }
    /* reset latch status */
    uint8_t cmd = CY8CMBRX_CMD_RESET_LATCH;
    write_bytes( cy8_mux_port, CY8CMBRX_CTRL_CMD_ADR, &cmd, 1 );
    return result; 
}


int write_bytes( tildagon_mux_i2c_obj_t* mux_port, uint8_t reg_adr, uint8_t* data, uint8_t length )
{
    uint8_t i2c_buffer[length+1];
    i2c_buffer[0] = reg_adr;
    for ( uint8_t i = 0; i < length; i++)
    {
        i2c_buffer[i+1] = data[i];
    }
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &reg_adr },
                                       { .len = length + 1, .buf = i2c_buffer } };
    tildagon_mux_i2c_transaction( mux_port, CY8CMBRX_ADDRESS, 1, &buffer[0], WRITE );
    return tildagon_mux_i2c_transaction( mux_port, CY8CMBRX_ADDRESS, 1, &buffer[1], WRITE );
}
