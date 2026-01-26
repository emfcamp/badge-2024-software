
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
 * @param state the comms state object
 * @param fusb the object for the fusb to use
 */
void fusbpd_decode( pd_state_t* state, fusb_state_t* fusb )
{
    /* parse rx buffer */
    while ( !fusb_rx_empty( fusb ) )
    {
        uint8_t buffer = 0;
        fusb_get_fifo( fusb, &buffer, 1U );
        if ( buffer == RX_SOP )
        {
            pd_header_union_t header;
            fusb_get_fifo( fusb, header.raw, 2U ); 
            
            if ( header.sop.number_objects == 0U )
            {
                /* handle control messages */
                state->last_rx_control_msg_type = header.sop.message_type;
            }
            else
            {
                /* handle data messages */
                if ( ( header.sop.message_type == PD_DATA_SOURCE_CAPABILITIES )
                  || ( header.sop.message_type == PD_DATA_REQUEST ) )
                {
                    for ( uint8_t i = 8U; i; i-- )
                    {
                        state->pdos[i].raw32 = 0U;   
                    }
                    fusb_get_fifo( fusb, (uint8_t*)&state->pdos[0].raw32, ( header.sop.number_objects * 4U ) ); 
                    state->number_of_pdos = header.sop.number_objects;
                    /* discard crc and end of packet */
                    uint8_t temp[4];
                    fusb_get_fifo( fusb, temp, 4U ); 
                }
                else if ( header.sop.message_type == PD_DATA_VENDOR_DEFINED )
                {
                    fusb_get_fifo( fusb, state->vendor.vendor_data, ( header.sop.number_objects * 4U ) ); 
                    state->vendor.no_objects = header.sop.number_objects;
                    /* discard crc and end of packet */
                    uint8_t temp[4];
                    fusb_get_fifo( fusb, temp, 4U );
                }
                else 
                {
                    /* let outer loop consume the message */
                }
                
                state->last_rx_data_msg_type = header.sop.message_type;
            }
        }
        else if ( buffer == RX_SOP1 )
        {
            if ( state->extra != NULL )
            {
                /* store for python */
                fusb_get_fifo( fusb, state->extra->prime.header.raw, 2U );
                uint8_t i = 0U;
                while( !fusb_rx_empty( fusb ) && ( i < 80U ) )
                {
                    fusb_get_fifo( fusb, &state->extra->prime.data[i], 1U );
                    i++;
                }
                state->extra->prime.data_size = i;
                state->extra->prime.new_msg = true;
            }
        }
        else if ( buffer == RX_SOP2 )
        {
            if ( state->extra != NULL )
            {
                /* store for python */
                fusb_get_fifo( fusb, state->extra->dbl_prime.header.raw, 2U );
                uint8_t i = 0U;
                while( !fusb_rx_empty( fusb ) && ( i < 80U ) )
                {
                    fusb_get_fifo( fusb, &state->extra->dbl_prime.data[i], 1U );
                    i++;
                }
                state->extra->dbl_prime.data_size = i;
                state->extra->dbl_prime.new_msg = true;
            }
        }
    }
}

/**
 * @brief creat a request power message 
 * @param state the comms state object
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
 * @param state the comms state object
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
 * @brief create a vendor specific pdo message.
 * @param state the comms state object.
 * @param data buffer of data to transmit, multiple of 4. first 4 bytes must be the vendor header.
 * @param no_objects number of VDOs to transmit.  max 7 objects including vendor header
 */
void fusbpd_vendor_specific( pd_state_t* state, uint8_t* data, uint8_t no_objects )
{
    if( no_objects < 8 )
    {
        state->tx_buffer[0] = TX_FIFO_ADDRESS;
        state->tx_buffer[1] = TX_SOP1; 
        state->tx_buffer[2] = TX_SOP1; 
        state->tx_buffer[3] = TX_SOP1; 
        state->tx_buffer[4] = TX_SOP2; 
        state->tx_buffer[5] = TX_PACKSYM | (0x02 + ( no_objects * 4 )) ;    
        pd_header_union_t header = { 0U };
        header.sop.number_objects = no_objects;
        header.sop.message_id = state->msg_id;
        header.sop.message_type = 0x0FU;
        header.sop.revision = 0x01U;
        header.sop.data_role = state->data_role;
        header.sop.power_role = state->power_role;
        state->tx_buffer[6] = header.raw[0]; 
        state->tx_buffer[7] = header.raw[1];
        state->msg_id++;
        uint8_t index = 0U;
        while( index < ( no_objects * 4 ) )
        {
            state->tx_buffer[ 8 + index ] = data[index];   
            index++; 
        }
        
        state->tx_buffer[ 8 + index ] = TX_JAM_CRC;
        state->tx_buffer[ 9 + index ] = TX_EOP;
        state->tx_buffer[ 10 + index ] = TX_OFF;
        state->tx_buffer[ 11 + index ] = TX_ON;
        state->message_length =  12 + index ;
    }
    else
    {
        /* todo return some error codes */
    }
}

/**
 * @brief create a prime message.
 * @param state the comms state object.
 * @param header standard message header.
 * @param data buffer of data to transmit.
 * @param length data length. fusb302 tx buffer is 48 bytes, 16 are needed for tx commands, length 32 max.
 */
void fusbpd_prime( pd_state_t* state, uint16_t header, uint8_t* data, uint8_t length )
{
    /* fill header with protocol layer state */
    pd_header_union_t msgheader = { 0U };
    msgheader.all = header;
    msgheader.sop.message_id = state->msg_id;
    msgheader.sop.revision = 0x01U;
    msgheader.sop.data_role = state->data_role;
    msgheader.sop.power_role = state->power_role;
    state->msg_id++;
    if( state->msg_id > 7 )
    {
        state->msg_id = 0;
    }
    
    state->tx_buffer[0] = TX_FIFO_ADDRESS;
    state->tx_buffer[1] = TX_SOP1; 
    state->tx_buffer[2] = TX_SOP1; 
    state->tx_buffer[3] = TX_SOP3; 
    state->tx_buffer[4] = TX_SOP3; 
    uint8_t padding = 0;
    if( length % 4 )
    {
        padding = 4 - ( length % 4 );
    }
    
    state->tx_buffer[5] = TX_PACKSYM | (length + 2 + padding);
    state->tx_buffer[6] = msgheader.raw[0];
    state->tx_buffer[7] = msgheader.raw[1];
    
    uint8_t index = 0U;
    while( index < length )
    {
        state->tx_buffer[ 8 + index ] = data[index];   
        index++; 
    }
    
    if( padding )
    {
        while( index < ( length + padding ) )
        {
            state->tx_buffer[ 8 + index ] = 0;   
            index++;
        }
    }
    
    state->tx_buffer[ 9 + index ] = TX_JAM_CRC;
    state->tx_buffer[ 10 + index ] = TX_EOP;
    state->tx_buffer[ 11 + index ] = TX_OFF;
    state->tx_buffer[ 12 + index ] = TX_ON;
    state->message_length =  13 + index ;
}

/**
 * @brief create a double prime message.
 * @param state the comms state object.
 * @param header standard message header.
 * @param data buffer of data to transmit.
 * @param length data length. fusb302 tx buffer is 48 bytes, 16 are needed for tx commands, length 32 max.
 */
void fusbpd_dbl_prime( pd_state_t* state, uint16_t header, uint8_t* data, uint8_t length )
{
    /* fill header with protocol layer state */
    pd_header_union_t msgheader = { 0U };
    msgheader.all = header;
    msgheader.sop.message_id = state->msg_id;
    msgheader.sop.revision = 0x01U;
    msgheader.sop.data_role = state->data_role;
    msgheader.sop.power_role = state->power_role;
    state->msg_id++;
    if( state->msg_id > 7 )
    {
        state->msg_id = 0;
    }
    
    state->tx_buffer[0] = TX_FIFO_ADDRESS;
    state->tx_buffer[1] = TX_SOP1; 
    state->tx_buffer[2] = TX_SOP3; 
    state->tx_buffer[3] = TX_SOP1; 
    state->tx_buffer[4] = TX_SOP3; 
    uint8_t padding = 0;
    if( length % 4 )
    {
        padding = 4 - ( length % 4 );
    }
    
    state->tx_buffer[5] = TX_PACKSYM | (length + 2 + padding);
    state->tx_buffer[6] = msgheader.raw[0];
    state->tx_buffer[7] = msgheader.raw[1];
    
    uint8_t index = 0U;
    while( index < length )
    {
        state->tx_buffer[ 8 + index ] = data[index];   
        index++; 
    }
        
    if( padding )
    {
        while( index < ( length + padding ) )
        {
            state->tx_buffer[ 8 + index ] = 0;   
            index++;
        }
    }
    
    state->tx_buffer[ 9 + index ] = TX_JAM_CRC;
    state->tx_buffer[ 10 + index ] = TX_EOP;
    state->tx_buffer[ 11 + index ] = TX_OFF;
    state->tx_buffer[ 12 + index ] = TX_ON;
    state->message_length =  13 + index ;
}
