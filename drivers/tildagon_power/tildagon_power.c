#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/idf_additions.h"
#include "esp_task.h"
#include "esp_random.h"
#include "driver/i2c_master.h"
#include "modmachine.h"
#include "tildagon_pin.h"

#include "tildagon_power.h"
#include "mp_power_event.h"

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
    POWER_REQUESTED    = 0x02,
    PSU_READY_RECEIVED = 0x03,
    BADGE_TO_BADGE     = 0x04,
    LANYARD            = 0x05,
    REQUEST_RETRY_FAIL = 0x06,
    VENDOR_SENT        = 0x07,
    VENDOR_RETRY_FAIL  = 0x08,
} pd_machine_state_t;

typedef enum 
{
    NO_EVENT,
    INTERRUPT_EVENT,
    HOST_TOGGLE,
    HOST_ATTACH,
    HOST_DETACH,
    HOST_GOODCRCSENT,
    HOST_TX_SENT,
    HOST_MAX_EVENT,
    DEVICE_TOGGLE,
    DEVICE_ATTACH,
    DEVICE_DETACH,
    DEVICE_GOODCRCSENT,
    DEVICE_TX_SENT,
    DEVICE_BC_LEVEL, 
} event_t;

typedef void (*funptr_t)( event_t );

void host_disabled_handler( event_t event );
void host_unattached_handler( event_t event );
void host_attached_handler ( event_t event );
void device_disabled_handler ( event_t event );
void device_unattached_handler( event_t event );
void device_attached_handler( event_t event );
void device_pd_machine ( event_t event );
void generate_events( void );
void determine_input_current_limit ( usb_state_t* state );
void clean_in( void );
void clean_out( void );


funptr_t host_attach_machine[MAX_STATES] =  
{
    host_disabled_handler,
    host_unattached_handler,
    host_attached_handler,
};

funptr_t device_attach_machine[MAX_STATES] =  
{
    device_disabled_handler,
    device_unattached_handler,
    device_attached_handler,
};

bq_state_t pmic = { 0 };
usb_state_t usb_in = { 0 };
usb_state_t usb_out = { 0 };

static attach_machine_state_t host_attach_state = DISABLED;
static attach_machine_state_t device_attach_state = DISABLED;
static pd_machine_state_t host_pd_state = NOT_STARTED;
static pd_machine_state_t device_pd_state = NOT_STARTED;
static TaskHandle_t tildagon_power_task_handle = NULL;
static QueueHandle_t event_queue;
bool lanyard_mode = false;

/**
 * @brief fast rate task to handle the interrupt generated events
 */
void tildagon_power_fast_task(void *param __attribute__((__unused__)))
{
    event_queue = xQueueCreate( 10, sizeof(event_t) );     
    usb_in.fusb.mux_port = tildagon_get_mux_obj( 7 );
    usb_out.fusb.mux_port = tildagon_get_mux_obj( 0 );
    pmic.mux_port = tildagon_get_mux_obj( 7 );
    // turn off 5V switch before setting up PMIC as the reset will enable the boost.
    aw9523b_pin_set_output( &ext_pin[2], 4, false);
    bq_init( &pmic );
    
    /* initialise isr */ 
    //todo move to allow sharing of sys_int isr
    machine_pins_init();
    gpio_set_intr_type(GPIO_NUM_10, GPIO_INTR_NEGEDGE );
    gpio_isr_handler_add( GPIO_NUM_10, tildagon_power_interrupt_event, NULL );
    
    clean_in();
    clean_out();
    
    /* determine the current state */
    fusb_get_status( &usb_in.fusb );
    fusb_get_statusa( &usb_in.fusb );
    if ( usb_in.fusb.statusa & FUSB_STATUSA_TOGGLE_MASK )
    {
        const event_t event = DEVICE_TOGGLE;
        xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );
    }
    
    fusb_get_status( &usb_out.fusb );
    fusb_get_statusa( &usb_out.fusb );
    if ( usb_out.fusb.statusa & FUSB_STATUSA_TOGGLE_MASK )
    {
        const event_t event = HOST_TOGGLE;
        xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );
    }
      
    bq_update_state( &pmic );
    /* 
        The interrupt adds an event to the queue to trigger a read over I2C
        as the freertos has a thread safe accessor to the queue  
    */
    if ( event_queue != NULL ) 
    {
        while ( 1 )
        {
            event_t event = NO_EVENT;
            if ( xQueueReceive(event_queue, &event, portMAX_DELAY) )
            {
                if ( ( event == NO_EVENT ) )
                {
                    /* this may happen if portMAX_DELAY isn't configured to block forever */
                }
                else if ( ( event == INTERRUPT_EVENT ) )
                {
                    generate_events();
                }
                else if ( event < HOST_MAX_EVENT )
                {
                    (*host_attach_machine[host_attach_state])( event );
                }
                else if ( !lanyard_mode )
                {
                    (*device_attach_machine[device_attach_state])( event );
                }
                else
                {
                    /*  throw away */
                }
            }
        }
    }
}

/**
 * @brief initialise the badge power management task
 */
void tildagon_power_init( void )
{
    xTaskCreatePinnedToCore(tildagon_power_fast_task, "power_task", 2048, NULL, tskIDLE_PRIORITY+3, &tildagon_power_task_handle, 0);
}

/**
 * @brief add an interrupt event to the queue. intended to be called from an ISR
 */
void tildagon_power_interrupt_event( void* param )
{
    BaseType_t TaskWoken;
    TaskWoken = pdFALSE;
    const event_t event = INTERRUPT_EVENT;
    xQueueSendToBackFromISR( event_queue, (void*)&event, &TaskWoken );
}

/**
 * @brief disconnect the battery to allow turn off on usb is disconnect
 */
void tildagon_power_off( void )
{
    aw9523b_pin_set_output( &ext_pin[2], 4, false);
    bq_disconnect_battery( &pmic );
}

/**
 * @brief turn the 5V supply on or off
 */
void tildagon_power_enable_5v( bool enable )
{
    if ( enable )
    {
        bq_enable_boost( &pmic, 1 );
        aw9523b_pin_set_output( &ext_pin[2], 4, true);
    }
    else
    {
        /* open switch then disable 5V */
        aw9523b_pin_set_output( &ext_pin[2], 4, false);
        bq_enable_boost( &pmic, 0 );
        bq_enable_HiZ_input( &pmic, 0 );
    }    
}

/**
 * @brief handler for host events possible when nothing is attached
 */
void host_disabled_handler( event_t event )
{
    if( event == HOST_TOGGLE )
    {
        host_attach_state = UNATTACHED;
        usb_out.fusb.cc_select = ( usb_out.fusb.statusa >> FUSB_STATUSA_TOGGLE_SHIFT ) & 0x03;
        fusb_mask_interrupt_toggle( &usb_out.fusb, 1 );
        fusb_stop_toggle(&usb_out.fusb );
        fusb_mask_interrupt_bclevel( &usb_out.fusb, 0 );
        fusb_mask_interrupt_comp( &usb_out.fusb, 0 );
        fusb_set_cc( &usb_out.fusb, usb_out.fusb.cc_select );
    }
}

/**
 * @brief handler for host events to detect attach
 */
void host_unattached_handler( event_t event )
{
    if( event == HOST_ATTACH )
    {
        host_attach_state = ATTACHED;
        fusb_mask_interrupt_bclevel( &usb_out.fusb, 1 );
        tildagon_power_enable_5v(true);    
        fusb_setup_pd(&usb_out.fusb );        
        fusb_mask_interrupt_retryfail( &usb_out.fusb, 0 );
        fusb_mask_interrupt_txsent( &usb_out.fusb, 0 );
        fusbpd_vendor_specific( &usb_out.pd );
        fusb_send ( &usb_out.fusb, usb_out.pd.tx_buffer, usb_out.pd.message_length );
        host_pd_state = VENDOR_SENT;
        push_event( MP_POWER_EVENT_HOST_ATTACH );
    }
}

/**
 * @brief handler for events while attached
 */
void host_attached_handler( event_t event )
{
    if( event == HOST_DETACH )
    {
        host_attach_state = DISABLED;
        clean_out();
        push_event( MP_POWER_EVENT_HOST_DETACH );
    }
    else
    {
        //todo host pd state machine for badge to badge
        if ( host_pd_state > NOT_STARTED )
        {
            //host_pd_machine( event );
        }
    }
}


/**
 * @brief handler for device events possible when nothing is attached
 */
void device_disabled_handler( event_t event )
{
    if( event == DEVICE_TOGGLE )
    {
        device_attach_state = UNATTACHED;
        fusb_mask_interrupt_toggle( &usb_in.fusb, 1 );
        /* use toggle status to get which CC line to use for PD */
        fusb_mask_interrupt_bclevel( &usb_in.fusb, 0 );
        usb_in.fusb.cc_select = ( usb_in.fusb.statusa >> FUSB_STATUSA_TOGGLE_SHIFT ) & 0x03;
        fusb_set_cc( &usb_in.fusb, usb_in.fusb.cc_select );
        if ( usb_in.fusb.status & FUSB_STATUS_VBUSOK_MASK )
        {
            const event_t event = DEVICE_ATTACH;
            xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );
        }
    }
}

/**
 * @brief handler for device events to detect attach
 */
void device_unattached_handler( event_t event )
{
    if ( event == DEVICE_ATTACH )
    {
        device_attach_state = ATTACHED;
        push_event( MP_POWER_EVENT_DEVICE_ATTACH );
    } 
    else if ( event == DEVICE_BC_LEVEL )
    {
        determine_input_current_limit( &usb_in );
        if ( ( usb_in.fusb.input_current_limit >= 1500 ) && ( device_pd_state == NOT_STARTED ) )
        {
            fusb_setup_pd( &usb_in.fusb );
            device_pd_state = WAITING;
        }
        fusb_mask_interrupt_bclevel( &usb_in.fusb, 1 );
    }
}

/**
 * @brief handler for device events while attached
 */
void device_attached_handler( event_t event )
{
    if ( event == DEVICE_DETACH)
    {
        device_attach_state = DISABLED;
        clean_in();
        push_event( MP_POWER_EVENT_DEVICE_DETACH );
    }
    else if ( event == DEVICE_BC_LEVEL )
    {
        determine_input_current_limit( &usb_in );
        if ( ( usb_in.fusb.input_current_limit >= 1500 ) && ( device_pd_state == NOT_STARTED ) )
        {
            fusb_setup_pd( &usb_in.fusb );
            device_pd_state = WAITING;
        }
        fusb_mask_interrupt_bclevel( &usb_in.fusb, 1 );
    }
    else
    {
        if ( device_pd_state > NOT_STARTED )
        {
            device_pd_machine( event );
        }
    }
}


/**
 * @brief state machine for the device pd comms
 */
void device_pd_machine ( event_t event )
{
    switch ( device_pd_state )
    {
        case WAITING:
        {
            if ( event == DEVICE_GOODCRCSENT )
            {          
                fusbpd_decode( &usb_in.pd, &usb_in.fusb );
                if ( usb_in.pd.last_rx_data_msg_type == PD_DATA_SOURCE_CAPABILITIES )
                {
                    /*
                        We only need 5V so can use the first object, from the usb 3 standard:
                        The vSafe5V Fixed Supply Object Shall always be the first object.
                        A Source Shall Not offer multiple Power Data Objects of the same 
                        type (fixed, variable, Battery) and the same Voltage but Shall 
                        instead offer one Power Data Object with the highest available 
                        current for that Source capability and Voltage. 
                        
                    */
                    uint32_t current = usb_in.pd.pdos[0].fixed.max_current * 10;
                    /* limit current to the maximum current of a non active cable */
                    if ( current > 3000 )
                    {
                        current = 3000;
                    }
                    fusbpd_request_power( &usb_in.pd, 0, current, current );
                    fusb_send( &usb_in.fusb, usb_in.pd.tx_buffer, usb_in.pd.message_length );  
                    usb_in.pd.last_rx_data_msg_type = PD_DATA_DO_NOT_USE; 
                    device_pd_state = POWER_REQUESTED;
                }          
                else if( usb_in.pd.last_rx_data_msg_type == PD_DATA_VENDOR_DEFINED )
                {
                    /* ToDo: if vendor pdo received decide on badge to badge and callback? */    
                }
            }
            break;
        }
        case POWER_REQUESTED:
        {
            if ( event == DEVICE_GOODCRCSENT )
            {
                fusb_auto_good_crc( &usb_in.fusb );
                fusbpd_decode( &usb_in.pd, &usb_in.fusb );   
                /* if psu ready move state */
                if ( usb_in.pd.last_rx_control_msg_type == PD_CONTROL_PS_RDY )
                {
                    device_pd_state = PSU_READY_RECEIVED;
                }
            }
            break;
        }
        case PSU_READY_RECEIVED:
        case BADGE_TO_BADGE:
        default:
        {
            /* stay in this state until detach */   
        }
    }
}  


/**
 * @brief Determines if the interrupt was a USB event and which one.
 */
void generate_events( void )
{
    uint8_t prev_status = pmic.status;
    uint8_t prev_faut = pmic.fault;
    
    bq_update_state( &pmic );
    if ( ( pmic.vbus > 2.6 ) && ( pmic.vbus < 4.3 ) )
    {
        bq_enable_HiZ_input( &pmic, 1 );
        lanyard_mode = true;
        push_event(MP_POWER_EVENT_LANYARD_ATTACH);
    }
    if ( prev_status == pmic.status )
    {
        uint8_t status_change = prev_status ^ pmic.status;
        if ( status_change & BQ_CHARGE_STAT_MASK )
        {
            push_event( MP_POWER_EVENT_CHARGE );
        }
    }
    if ( ( prev_faut ^ pmic.fault ) & 0x71 )
    {
        push_event( MP_POWER_EVENT_FAULT );
    }
    while ( gpio_get_level( GPIO_NUM_10 ) == 0 )
    {
        if ( gpio_get_level( GPIO_NUM_10 ) == 0 )
        {
            uint16_t interruptab = fusb_get_interruptab( &usb_in.fusb );
            uint8_t interrupt = fusb_get_interrupt( &usb_in.fusb );
            fusb_get_status( &usb_in.fusb );
            fusb_get_statusa( &usb_in.fusb );
            if( interruptab & FUSB_TOGGLE_I_MASK ) 
            {
                const event_t event = DEVICE_TOGGLE;
                xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );
            }
            if( ( interrupt & FUSB_VBUSOK_I_MASK ) && ( usb_in.fusb.status & FUSB_STATUS_VBUSOK_MASK ) )
            {
                const event_t event = DEVICE_ATTACH;
                xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );
            }
            else if ( ( interrupt & FUSB_VBUSOK_I_MASK ) && ( ( usb_in.fusb.status & FUSB_STATUS_VBUSOK_MASK ) == 0 ) )
            {
                const event_t event = DEVICE_DETACH;
                xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );  
            }
            if ( device_pd_state > NOT_STARTED )
            {
                if ( interruptab & FUSB_GD_CRC_I_MASK )
                {
                    const event_t event = DEVICE_GOODCRCSENT;
                    xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );
                }
                if ( interruptab & FUSB_TXSENT_I_MASK )
                {
                    usb_in.pd.msg_id++;
                }
            } 
            else if ( interrupt & FUSB_BC_LVL_I_MASK )
            {
                const event_t event = DEVICE_BC_LEVEL;
                xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );  
            }
        }
    
        if ( gpio_get_level( GPIO_NUM_10 ) == 0 )
        {
            uint16_t interruptab = fusb_get_interruptab( &usb_out.fusb );
            uint8_t interrupt = fusb_get_interrupt( &usb_out.fusb );
            fusb_get_status( &usb_out.fusb );
            fusb_get_statusa( &usb_out.fusb );

            if ( interruptab & FUSB_TOGGLE_I_MASK )
            { 
                const event_t event = HOST_TOGGLE;
                xQueueSendToBack(event_queue, (void*)&event, (TickType_t)0 );
            }
            if ( ( ( ( usb_out.fusb.status & FUSB_STATUS_COMP_MASK ) == 0U ) && ( interrupt & FUSB_CMPCHG_I_MASK ) ) 
            || ( ( interrupt & FUSB_BC_LVL_I_MASK ) && ( ( usb_out.fusb.status & FUSB_STATUS_BCLVL_MASK ) < 3 ) ) )
            {
                const event_t event = HOST_ATTACH;
                xQueueSendToBack(event_queue, (void*)&event, (TickType_t)0 );
            }
            else if ( ( usb_out.fusb.status & FUSB_STATUS_COMP_MASK ) && ( interrupt & FUSB_CMPCHG_I_MASK ) )
            {
                const event_t event = HOST_DETACH;
                xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );  
            }
            if( host_pd_state > NOT_STARTED )
            {
                if ( interruptab & FUSB_GD_CRC_I_MASK )
                {
                    const event_t event = HOST_GOODCRCSENT;
                    xQueueSendToBack(event_queue, (void*)&event , (TickType_t)0 );
                } 
                if ( interruptab & FUSB_TXSENT_I_MASK )
                {
                    usb_out.pd.msg_id++;
                }
            }
        }
    }
}

/**
 * @brief figure out the input current limit of the supply
 */
void determine_input_current_limit ( usb_state_t* state )
{
    state->fusb.input_current_limit = 500;
    uint16_t bc_level = state->fusb.status & FUSB_STATUS_BCLVL_MASK;
    if ( bc_level > 0 )
    {
        if ( bc_level == 2 )
        {
            state->fusb.input_current_limit = 1500U;
        }
        else if ( ( bc_level == 3 ) && ( ( state->fusb.status & FUSB_STATUS_COMP_MASK ) == 0 ) )
        {
            state->fusb.input_current_limit = 3000U;
        }
    }
    bq_set_input_current_limit( &pmic, (float) state->fusb.input_current_limit );
}

/**
 * @brief reset the device port to the initial state
 */
void clean_in( void )
{
    usb_in.fusb.input_current_limit = 500;
    bq_set_input_current_limit( &pmic, (float) usb_in.fusb.input_current_limit );
    device_pd_state = NOT_STARTED;
    usb_in.fusb.cc_select = 0U;
    fusb_setup_device( &usb_in.fusb );
    usb_in.pd.last_rx_control_msg_type = 0U;
    usb_in.pd.last_rx_data_msg_type = 0U;
    usb_in.pd.number_of_pdos = 0U;
    *((uint16_t*)&usb_in.pd.last_rx_header.raw[0]) = 0U;
    usb_in.pd.msg_id = 0U;
    *((uint32_t*)&usb_in.pd.rx_badge_id[0]) = 0U;
    *((uint32_t*)&usb_in.pd.rx_badge_id[4]) = 0U;
}

/**
 * @brief reset the host port to the initial state
 */
void clean_out( void )
{
    tildagon_power_enable_5v(false);
    host_pd_state = NOT_STARTED;
    usb_in.fusb.cc_select = 0;
    fusb_setup_host( &usb_out.fusb );
    usb_out.pd.last_rx_control_msg_type = 0U;
    usb_out.pd.last_rx_data_msg_type = 0U;   
    usb_out.pd.number_of_pdos = 0U;
    usb_out.pd.msg_id = 0U;
     
    *((uint16_t*)&usb_out.pd.last_rx_header.raw[0]) = 0U;
    *((uint32_t*)&usb_out.pd.rx_badge_id[0]) = 0U;
    *((uint32_t*)&usb_out.pd.rx_badge_id[4]) = 0U;
    
    /* setup lanyard and badge to badge numbers */
    esp_fill_random( usb_in.pd.badge_id, 8 );
    for ( uint8_t i = 0; i < 8; i++)
    {
        usb_out.pd.badge_id[i] = usb_in.pd.badge_id[i];
    }
    
    if ( lanyard_mode )
    {
        lanyard_mode = false;
        clean_in();
        push_event(MP_POWER_EVENT_LANYARD_DETACH);
    }
}

