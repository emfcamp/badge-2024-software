
#ifndef FUSB302B_H
#define FUSB302B_H

#include <stdint.h>
#include "tildagon_i2c.h"

#define FUSB_TXSENT_I_MASK (uint16_t)0x0004U
#define FUSB_TOGGLE_I_MASK (uint16_t)0x0040U
#define FUSB_GD_CRC_I_MASK (uint16_t)0x0100U
#define FUSB_BC_LVL_I_MASK (uint8_t)0x01U
#define FUSB_CMPCHG_I_MASK (uint8_t)0x20U
#define FUSB_VBUSOK_I_MASK (uint8_t)0x80U

#define FUSB_STATUSA_TOGGLE_MASK (uint16_t)0x3800U
#define FUSB_STATUSA_TOGGLE_SHIFT (int8_t)11
#define FUSB_STATUS_COMP_MASK   (uint16_t)0x0020U
#define FUSB_STATUS_BCLVL_MASK  (uint16_t)0x0003U
#define FUSB_STATUS_VBUSOK_MASK (uint16_t)0x0080U

typedef struct
{
    tildagon_mux_i2c_obj_t* mux_port;
    uint8_t cc_select;
    uint16_t input_current_limit;
    uint16_t status;
    uint16_t statusa;
    uint8_t host;
} fusb_state_t;

/**
 * @brief Initialise the fusb302 to a device
 * @details reset the device then set comparator threshold to 2.226V, enable Vbus measurement,
 * flush buffers, enable interrupts, 3 retries and Vbus, BC level and good crc interrupts, enable toggle
 * @param state the port object
 */
extern void fusb_setup_device( fusb_state_t* state );
/**
 * @brief Initialise the fusb302 to a host
 * @details reset then setup pull ups, data roles, cc measurement level, enable toggle
 * and toggle interrupt, 1.5A current limit, 3 auto retries and flush buffers
 * @param state the port object
 */
extern void fusb_setup_host( fusb_state_t* state );
/**
 * @brief set the measurement to a cc line
 * @param state the port object
 * @param cc_select the pin to measure on
 */
extern void fusb_set_cc( fusb_state_t* state, uint8_t cc_select );
/**
 * @brief disable toggle
 * @param state the port object
 */
extern void fusb_stop_toggle( fusb_state_t* state );
/**
 * @brief status read from the device
 * @param state the port object
 */
extern void fusb_get_status( fusb_state_t* state );
/**
 * @brief statusa read from the device
 * @param state the port object
 */
extern void fusb_get_statusa( fusb_state_t* state );
/**
 * @brief read interrupt a and b registers
 * @param state the port object
 */
extern uint16_t fusb_get_interruptab( fusb_state_t* state );
/**
 * @brief read interrupt register
 * @param state the port object
 */
extern uint8_t fusb_get_interrupt( fusb_state_t* state );
/**
 * @brief setup the PD to send the good CRC packet automatically
 * @param state the port object
 */
extern void fusb_auto_good_crc ( fusb_state_t* state );
/**
 * @brief flush both the rx and tx buffers
 * @param state the port object
 */
extern void fusb_flush_buffers( fusb_state_t* state );
/**
 * @brief mask toggle interrupt
 * @param state the port object
 * @param value of mask
 */
extern void fusb_mask_interrupt_toggle( fusb_state_t* state, uint8_t value );
/**
 * @brief mask comparator interrupt
 * @param state the port object
 * @param value of mask
 */
extern void fusb_mask_interrupt_comp( fusb_state_t* state, uint8_t value );
/**
 * @brief mask BC level interrupt
 * @param state the port object
 * @param value of mask
 */
extern void fusb_mask_interrupt_bclevel( fusb_state_t* state, uint8_t value );
/**
 * @brief mask PD good CRC interrupt
 * @param state the port object
 * @param value of mask
 */
extern void fusb_mask_interrupt_gdcrc( fusb_state_t* state, uint8_t value );
/**
 * @brief mask PD soft reset interrupt
 * @param state the port object
 * @param value of mask
 */
extern void fusb_mask_interrupt_softreset( fusb_state_t* state, uint8_t value );
/**
 * @brief mask PD hard reset interrupt
 * @param state the port object
 * @param value of mask
 */
extern void fusb_mask_interrupt_hardreset( fusb_state_t* state, uint8_t value );
/**
 * @brief mask PD retry failure interrupt
 * @param state the port object
 * @param value of mask
 */
extern void fusb_mask_interrupt_retryfail( fusb_state_t* state, uint8_t value );
/**
 * @brief mask PD tx sent got a good crc interrupt
 * @param state the port object
 * @param value of mask
 */
extern void fusb_mask_interrupt_txsent( fusb_state_t* state, uint8_t value );
/**
 *  @brief enable or disable comms based on cc_select
 * @param state the port object
 */ 
extern void fusb_setup_pd( fusb_state_t* state );
/**
 * @brief are bytes available 
 * @param state the port object
 */
extern uint8_t fusb_rx_empty( fusb_state_t* state );
/**
 * @brief get the contents of the rx fifo
 * @param state the port object
 * @param rx_buffer buffer to return the data of size length
 * @param length amount of data
 */
extern void fusb_get_fifo(fusb_state_t* state, uint8_t* rx_buffer, uint8_t length );
/**
 * @brief send a message to the tx fifo of up to PD_MAX_TX_MSG_SIZE bytes
 * @param state the port object
 * @param message buffer to send
 * @param length amount of data
 */
extern void fusb_send( fusb_state_t* state, uint8_t* message, uint8_t length  );

#endif /* FUSB302B_H */
