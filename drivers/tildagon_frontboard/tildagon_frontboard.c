

#include "cy8cmbrx.h"
#include "aw9523b.h"
#include "qmc6309.h"
#include "driver/gpio.h"
#include "tildagon_frontboard.h"
#include "tildagon_pin.h"
#include "tildagon_imu.h"
#include "mp_frontboard.h"
#include "esp_err.h"
    
#define READ ( MP_MACHINE_I2C_FLAG_WRITE1 | MP_MACHINE_I2C_FLAG_READ | MP_MACHINE_I2C_FLAG_STOP )
#define WRITE MP_MACHINE_I2C_FLAG_STOP

const uint8_t reset = 7U;
const uint8_t int_clear = 6U;
const uint8_t iox_int = 3U;
const uint8_t ls1 = 15U;

aw9523b_device_t top_egpio = 
{
    .i2c_addr = 0x58,
};

static void iox_cb ( void* args, uint8_t event );

/**
 * @brief initialise the frontboard
 */
void tildagon_frontboard_2026_init( void )
{
    /* setup frontboard port expander */
    top_egpio.mux = tildagon_get_mux_obj( TILDAGON_TOP_I2C_PORT ),
    tildagon_pins_set_aux( top_egpio, 0 );
    aw9523b_init( &ext_pin[3] );    
    aw9523b_pin_set_direction( &ext_pin[1], iox_int, true ); 
    aw9523b_irq_register( &ext_pin[1], iox_int, iox_cb, NULL );
    aw9523b_irq_enable( &ext_pin[1], iox_int );  
    
    /* raise reset and setup touch and proximity */
    aw9523b_pin_set_direction( &ext_pin[3], reset, false );
    aw9523b_pin_set_mode( &ext_pin[3], reset, AW9523B_PIN_MODE_GPIO );
    aw9523b_pin_set_output( &ext_pin[3], reset, true );
    
    if ( qmc6309_init() == ESP_OK )
    {
        tildagon_imu_register_compass( qmc6309_update, qmc6309_read );
    }
    cy8cmbrx_init( tildagon_get_mux_obj( TILDAGON_TOP_I2C_PORT ) );
}

/**
 * @brief callback for the top board port expander,
 * looks for cause of interrupt and calls the relevant isr
 */
static void iox_cb ( void* args, uint8_t event )
{
    aw9523b_irq_handler( &ext_pin[3] );   
}

/**
 * @brief callback for the cap sense 
 */
void cy8cmbrx_cb( void* args ,uint8_t event )
{
    cy8cmbrx_status_t status = cy8cmbrx_run();
    /* push events */
    for (uint8_t i = 0U; i < 2; i++)
    {
        if ( ( status.prox[i] == CY8CMBRX_RISING_EDGE ) || ( status.prox[i] == CY8CMBRX_PULSE ))
        {
            mp_frontboard2026_push_event( MP_PROX_EVENT_1 + i, MP_FB_RISING_EDGE);
        }
        if ( ( status.prox[i] == CY8CMBRX_FALLING_EDGE ) || ( status.prox[i] == CY8CMBRX_PULSE ))
        {
            mp_frontboard2026_push_event( MP_PROX_EVENT_1 + i, MP_FB_FALLING_EDGE);
        }
    }
    for (uint8_t i = 0U; i < 12; i++)
    {
        if ( ( status.buttons[i] == CY8CMBRX_RISING_EDGE ) || ( status.buttons[i] == CY8CMBRX_PULSE ))
        {
            mp_frontboard2026_push_event( MP_TOUCH_EVENT_1 + i, MP_FB_RISING_EDGE);
        }
        if ( ( status.buttons[i] == CY8CMBRX_FALLING_EDGE ) || ( status.buttons[i] == CY8CMBRX_PULSE ))
        {
            mp_frontboard2026_push_event( MP_TOUCH_EVENT_1 + i, MP_FB_FALLING_EDGE);
        }
    }
}


