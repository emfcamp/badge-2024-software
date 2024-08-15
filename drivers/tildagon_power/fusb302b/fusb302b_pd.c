
#include "fusb302b_pd.h"

#define TX_FIFO_ADDRESS 0x43U
/* FIFO tokens */
#define TX_ON      0xA1U
#define TX_SOP1    0x12U
#define TX_SOP2    0x13U
#define TX_SOP3    0x1BU
#define TX_RESET1  0x15U
#define TX_RESET2  0x16U
#define TX_PACKSYM 0x80U
#define TX_JAM_CRC 0xFFU
#define TX_EOP     0x14U
#define TX_OFF     0xFEU
#define RX_SOP     0xE0U
#define RX_SOP1    0xC0U
#define RX_SOP2    0xA0U
#define RX_SOP1DB  0x80U
#define RX_SOP2DB  0x60U

/**
 * @brief parse and decode the receive buffer
 * @param state the comms state onject
 * @param fusb the object for the fusb to use
 */
void fusbpd_decode( pd_state_t* state, fusb_state_t* fusb )
{
    uint8_t rx_buffer[32];
    /* parse rx buffer */
    while ( !fusb_rx_empty( fusb ) )
    {
        fusb_get_fifo( fusb, rx_buffer, 1 ); 
        if ( rx_buffer[0] == RX_SOP )
        {
            fusb_get_fifo( fusb, state->last_rx_header.raw, 2 ); 
            
            if ( state->last_rx_header.sop.number_objects == 0 )
            {
                /* handle control messages */
                state->last_rx_control_msg_type = state->last_rx_header.sop.message_type;
            }
            else
            {
                uint8_t buffer_index = 0U;
                if ( state->last_rx_header.sop.message_type == PD_DATA_SOURCE_CAPABILITIES )
                {
                    for ( uint8_t i = 8U; i; i-- )
                    {
                        state->pdos[i].raw32 = 0U;   
                    }
                    fusb_get_fifo( fusb, rx_buffer, ( state->last_rx_header.sop.number_objects * 4) + 4 ); 
                    for ( uint8_t i = 0U; i < state->last_rx_header.sop.number_objects; i++ )
                    {
                        state->pdos[i].raw32 = *((uint32_t*)&rx_buffer[ buffer_index ]);
                        buffer_index += 4U; 
                    }
                    state->number_of_pdos = state->last_rx_header.sop.number_objects;
                }
                else if ( state->last_rx_header.sop.message_type == PD_DATA_VENDOR_DEFINED )
                {
                    
                    fusb_get_fifo( fusb, rx_buffer, ( state->last_rx_header.sop.number_objects * 4) + 4 ); 
                    buffer_index += 2U;
                    uint16_t vendor_id = rx_buffer[ buffer_index ] + ( rx_buffer[ buffer_index + 1 ] << 8 ); 
                    buffer_index += 2U;
                    if ( vendor_id == PD_VENDOR_ID )
                    {      
                        *((uint32_t*)&state->rx_badge_id[0]) = *((uint32_t*)&rx_buffer[buffer_index]);
                        *((uint32_t*)&state->rx_badge_id[4]) = *((uint32_t*)&rx_buffer[buffer_index + 4]);
                        buffer_index += 8U;
                    }
                    else
                    {
                        //todo save this to pass to micropython?
                    }
                }
                else
                {
                }
                state->last_rx_data_msg_type = state->last_rx_header.sop.message_type;
            }
        }
    }
}

/**
 * @brief creat a request power message 
 * @param state the comms state onject
 * @param num the index of the pdo list sent from the source
 * @param current the current required to run the device
 * @param max_current the maximum current required by the device
 */
void fusbpd_request_power( pd_state_t* state, uint8_t num, uint16_t current, uint16_t max_current )
{
    state->tx_buffer[0] = TX_FIFO_ADDRESS;
    state->tx_buffer[1] = TX_SOP1;
    state->tx_buffer[2] = TX_SOP1;
    state->tx_buffer[3] = TX_SOP1;
    state->tx_buffer[4] = TX_SOP2;
    state->tx_buffer[5] = TX_PACKSYM | 0x06;
    state->tx_buffer[6] = ( 0x01 << 6 ) /* PD 2.0 */ | 0x02 /* request */;
    state->tx_buffer[7] = ( 0x01 << 4 ) /* object count */ | ( ( state->msg_id & 0x07 ) << 1 );
    state->msg_id++;
        
    /* packing max current into fields */
    uint16_t max_current_b = max_current / 10;
    state->tx_buffer[8] = max_current_b & 0xFF;
    state->tx_buffer[9] = max_current_b >> 8;
    
    /* packing current into fields */
    uint16_t current_b = current / 10;
    uint8_t current_l = current_b & 0x3f;
    state->tx_buffer[9] |= current_l << 2;
    state->tx_buffer[10] = current_b >> 6;

    state->tx_buffer[11] = ( (num+1) << 4 )/* object position */ | 0x01 /* no suspend */;
    state->tx_buffer[12] = TX_JAM_CRC;
    state->tx_buffer[13] = TX_EOP;
    state->tx_buffer[14] = TX_OFF;
    state->tx_buffer[15] = TX_ON;
    state->message_length = 16;
}   

/**
 * @brief create a request source capabilities message
 * @param state the comms state onject
 */          
void fusbpd_request_capability( pd_state_t* state )
{
    state->tx_buffer[0] = TX_FIFO_ADDRESS;
    state->tx_buffer[1] = TX_SOP1; 
    state->tx_buffer[2] = TX_SOP1; 
    state->tx_buffer[3] = TX_SOP1; 
    state->tx_buffer[4] = TX_SOP2; 
    state->tx_buffer[5] = TX_PACKSYM | 0x02; 
    state->tx_buffer[6] = 0x47U; 
    state->tx_buffer[7] = 0x00U | ( ( state->msg_id & 0x07 ) << 1 ) ;
    state->msg_id++;
    state->tx_buffer[8] = TX_JAM_CRC; 
    state->tx_buffer[9] = TX_EOP;
    state->tx_buffer[10] = TX_OFF; 
    state->tx_buffer[11] = TX_ON;  
    state->message_length = 12;
}

/**
 * @brief create a vendor specific pdo message with the esp32 unique id
 * @param state the comms state onject
 */
void fusbpd_vendor_specific( pd_state_t* state )
{
    state->tx_buffer[0] = TX_FIFO_ADDRESS;
    state->tx_buffer[1] = TX_SOP1; 
    state->tx_buffer[2] = TX_SOP1; 
    state->tx_buffer[3] = TX_SOP1; 
    state->tx_buffer[4] = TX_SOP2; 
    state->tx_buffer[5] = TX_PACKSYM | 0x0E;
    pd_header_union_t header = { 0U };
    header.sop.number_objects = 0x03U;
    header.sop.message_id = state->msg_id;
    header.sop.message_type = 0x0FU;
    header.sop.revision = 0x01U;
    header.sop.data_role = state->data_role;
    header.sop.power_role = state->power_role;
    state->tx_buffer[6] = header.raw[0]; 
    state->tx_buffer[7] = header.raw[1];
    state->msg_id++;
    state->tx_buffer[8] = 0x00U;
    state->tx_buffer[9] = 0x00U;
    state->tx_buffer[10] = PD_VENDOR_ID >> 8;
    state->tx_buffer[11] = PD_VENDOR_ID & 0XFF;
    state->tx_buffer[12] = state->badge_id[0];
    state->tx_buffer[13] = state->badge_id[1];
    state->tx_buffer[14] = state->badge_id[2];
    state->tx_buffer[15] = state->badge_id[3];
    state->tx_buffer[16] = state->badge_id[4];
    state->tx_buffer[17] = state->badge_id[5];
    state->tx_buffer[18] = state->badge_id[6];
    state->tx_buffer[19] = state->badge_id[7];
    state->tx_buffer[20] = TX_JAM_CRC;
    state->tx_buffer[21] = TX_EOP;
    state->tx_buffer[22] = TX_OFF;
    state->tx_buffer[23] = TX_ON;
    state->message_length = 24;
}
