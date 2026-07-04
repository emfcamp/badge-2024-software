
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
                fusb_get_fifo( fusb, &state->extra->prime.data[0], 2U );
                pd_header_union_t header;
                header.raw[0] = state->extra->prime.data[0];
                header.raw[1] = state->extra->prime.data[1];
                fusb_get_fifo( fusb, &state->extra->prime.data[2], header.sop_prime.number_objects * 4 );
                state->extra->prime.data_size = 2 + ( header.sop_prime.number_objects * 4 );
                state->extra->prime.new_msg = true;
            }
        }
        else if ( buffer == RX_SOP2 )
        {
            if ( state->extra != NULL )
            {
                /* store for python */
                fusb_get_fifo( fusb, &state->extra->dbl_prime.data[0], 2U );
                pd_header_union_t header;
                header.raw[0] = state->extra->dbl_prime.data[0];
                header.raw[1] = state->extra->dbl_prime.data[1];
                fusb_get_fifo( fusb, &state->extra->dbl_prime.data[2], header.sop_prime.number_objects * 4 );
                state->extra->dbl_prime.data_size = 2 + ( header.sop_prime.number_objects * 4 );
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
void fusbpd_prime( pd_state_t* state, uint8_t* data, uint8_t length )
{
    uint8_t len = length - 2U;
    /* fill header with protocol layer state */
    pd_header_union_t msgheader = { 0U };
    msgheader.raw[0] = data[0];
    msgheader.raw[1] = data[1];
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
    if( len % 4 )
    {
        padding = 4 - ( len % 4 );
    }
    
    state->tx_buffer[5] = TX_PACKSYM | (length + padding );
    state->tx_buffer[6] = msgheader.raw[0];
    state->tx_buffer[7] = msgheader.raw[1];
    
    uint8_t index = 0U;
    while( index < len )
    {
        state->tx_buffer[ 8 + index ] = (&data[2])[index];
        index++; 
    }
    
    if( padding )
    {
        while( index < ( len + padding ) )
        {
            state->tx_buffer[ 8 + index ] = 0;   
            index++;
        }
    }
    
    state->tx_buffer[ 8 + index ] = TX_JAM_CRC;
    state->tx_buffer[ 9 + index ] = TX_EOP;
    state->tx_buffer[ 10 + index ] = TX_OFF;
    state->tx_buffer[ 11 + index ] = TX_ON;
    state->message_length =  12 + index ;
}

/**
 * @brief create a double prime message.
 * @param state the comms state object.
 * @param header standard message header.
 * @param data buffer of data to transmit.
 * @param length data length. fusb302 tx buffer is 48 bytes, 16 are needed for tx commands, length 32 max.
 */
void fusbpd_dbl_prime( pd_state_t* state, uint8_t* data, uint8_t length )
{
    uint8_t len = length - 2U;
    /* fill header with protocol layer state */
    pd_header_union_t msgheader = { 0U };
    msgheader.raw[0] = data[0];
    msgheader.raw[1] = data[1];
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
    if( len % 4 )
    {
        padding = 4 - ( len % 4 );
    }
    
    state->tx_buffer[5] = TX_PACKSYM | (length + padding );
    state->tx_buffer[6] = msgheader.raw[0];
    state->tx_buffer[7] = msgheader.raw[1];
    
    uint8_t index = 0U;
    while( index < len )
    {
        state->tx_buffer[ 8 + index ] = (&data[2])[index];   
        index++; 
    }
        
    if( padding )
    {
        while( index < ( len + padding ) )
        {
            state->tx_buffer[ 8 + index ] = 0;   
            index++;
        }
    }
    
    state->tx_buffer[ 8 + index ] = TX_JAM_CRC;
    state->tx_buffer[ 9 + index ] = TX_EOP;
    state->tx_buffer[ 10 + index ] = TX_OFF;
    state->tx_buffer[ 11 + index ] = TX_ON;
    state->message_length =  12 + index ;
}

/**
 * @brief create discover identity response.
 * @param state the comms state object.
 */
void fusbpd_vendor_id( pd_state_t* state )
{
    state->tx_buffer[0] = TX_FIFO_ADDRESS;
    state->tx_buffer[1] = TX_SOP1; 
    state->tx_buffer[2] = TX_SOP1; 
    state->tx_buffer[3] = TX_SOP1; 
    state->tx_buffer[4] = TX_SOP2; 
    state->tx_buffer[5] = TX_PACKSYM | 0x12;   
     
    pd_header_union_t header = { 0U };
    header.sop.number_objects = 4;
    header.sop.message_id = state->msg_id;
    header.sop.message_type = 0x0FU;
    header.sop.revision = 0x01U;
    header.sop.data_role = state->data_role;
    header.sop.power_role = state->power_role;
    
    state->tx_buffer[6] = header.raw[0]; 
    state->tx_buffer[7] = header.raw[1];
    
    pd_vendor_header_union_t vdh = { 0 };
    vdh.header.vendor_id = 0xFF00U;
    vdh.header.lsb.structured.stuctured = 0x01U;
    vdh.header.lsb.structured.command_type = 0x01U;
    vdh.header.lsb.structured.command = PD_VEND_CMD_DISCOVER_IDENTITY;
    
    state->tx_buffer[8] = vdh.bytes[0]; 
    state->tx_buffer[9] = vdh.bytes[1]; 
    state->tx_buffer[10] = vdh.bytes[2]; 
    state->tx_buffer[11] = vdh.bytes[3]; 
    
    pd_vendor_id_header_union_t vid = { 0 };
    vid.header.usb_device = 0x01U;
    //vid.header.usb_host = 0x01U;
    vid.header.product_type = 0x01U;
    vid.header.vendor_id = 0x344FU;
    
    state->tx_buffer[12] = vid.bytes[0]; 
    state->tx_buffer[13] = vid.bytes[1]; 
    state->tx_buffer[14] = vid.bytes[2]; 
    state->tx_buffer[15] = vid.bytes[3]; 
    
    state->tx_buffer[16] = 0x00U;
    state->tx_buffer[17] = 0x00U; 
    state->tx_buffer[18] = 0x00U;
    state->tx_buffer[19] = 0x00U;
    
    pd_vendor_product_union_t vpdo = { 0U };
    //vpdo.product_data.product_id = 0x065E;
    //vpdo.product_data.device = 0x0001;
    
    state->tx_buffer[20] = vpdo.bytes[0];
    state->tx_buffer[21] = vpdo.bytes[1];
    state->tx_buffer[22] = vpdo.bytes[2];
    state->tx_buffer[23] = vpdo.bytes[3];
    
    state->tx_buffer[24] = TX_JAM_CRC;
    state->tx_buffer[25] = TX_EOP;
    state->tx_buffer[26] = TX_OFF;
    state->tx_buffer[27] = TX_ON;
    state->message_length =  28;
    
    state->msg_id++;
}


/**
 * @brief create a reject command.
 * @param state the comms state object.
 */
void fusbpd_reject( pd_state_t* state )
{
    state->tx_buffer[0] = TX_FIFO_ADDRESS;
    state->tx_buffer[1] = TX_SOP1; 
    state->tx_buffer[2] = TX_SOP1; 
    state->tx_buffer[3] = TX_SOP1; 
    state->tx_buffer[4] = TX_SOP2; 
    state->tx_buffer[5] = TX_PACKSYM | 0x02;   
     
    pd_header_union_t header = { 0U };
    header.sop.number_objects = 0;
    header.sop.message_id = state->msg_id;
    header.sop.message_type = 0x04U;
    header.sop.revision = 0x01U;
    header.sop.data_role = state->data_role;
    header.sop.power_role = state->power_role;
    
    state->tx_buffer[6] = header.raw[0]; 
    state->tx_buffer[7] = header.raw[1];
 
    state->tx_buffer[8] = TX_JAM_CRC;
    state->tx_buffer[9] = TX_EOP;
    state->tx_buffer[10] = TX_OFF;
    state->tx_buffer[11] = TX_ON;
    state->message_length =  12;
    
    state->msg_id++;
}