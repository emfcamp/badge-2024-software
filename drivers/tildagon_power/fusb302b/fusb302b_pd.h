#ifndef FUSB302B_PD_H
#define FUSB302B_PD_H

#include <stdint.h>
#include "fusb302b.h"


#define PD_FIXED_SUPPLY 0U
#define PD_BATTERY 1U
#define PD_VARIABLE_SUPPLY 2U
#define PD_MAX_TX_MSG_SIZE 50 /* assume TXon command doesn't go into the fifo and one for the device address*/
/*
PD data structures
*/
typedef enum
{
    PD_CONTROL_DO_NOT_USE           = 0x00U,
    PD_CONTROL_GOODCRC              = 0x01U,
    PD_CONTROL_GOTOMIN              = 0x02U,
    PD_CONTROL_ACCEPT               = 0x03U, 
    PD_CONTROL_REJECT               = 0x04U,
    PD_CONTROL_PING                 = 0x05U,
    PD_CONTROL_PS_RDY               = 0x06U,
    PD_CONTROL_GET_SOURCE_CAP       = 0x07U,
    PD_CONTROL_GET_SINK_CAP         = 0x08U,
    PD_CONTROL_DATA_ROLE_SWAP       = 0x09U,
    PD_CONTROL_POWER_ROLE_SWAP      = 0x0AU,
    PD_CONTROL_VCONN_SWAP           = 0x0BU,
    PD_CONTROL_WAIT                 = 0x0CU,
    PD_CONTROL_SOFT_RESET           = 0x0DU, 
    PD_CONTROL_DATA_RESET           = 0x0EU,
    PD_CONTROL_DATA_RESET_COMPLETE  = 0x0FU,
    PD_CONTROL_NOT_SUPPORTED        = 0x10U,
    PD_CONTROL_GET_SRC_CAP_EXTENDED = 0x11U,
    PD_CONTROL_GET_STATUS           = 0x12U,  
    PD_CONTROL_FR_SWAP              = 0x13U,
    PD_CONTROL_GET_PPS_STATUS       = 0x14U,
    PD_CONTROL_COUNTRY_CODE         = 0x15U,
} pd_control_message_type_t;

typedef enum
{
    PD_DATA_DO_NOT_USE          = 0x00U,
    PD_DATA_SOURCE_CAPABILITIES = 0x01U,
    PD_DATA_REQUEST             = 0x02U,
    PD_DATA_BIST                = 0x03U,
    PD_DATA_SINK_CAPABILITIES   = 0x04U,
    PD_DATA_VENDOR_DEFINED      = 0x0FU,
} pd_data_message_types_t;

typedef enum
{
    PD_VEND_CMD_SHALL_NOT_BE_USED = 0x00U,
    PD_VEND_CMD_DISCOVER_IDENTITY = 0x01U,
    PD_VEND_CMD_DISCOVER_SVIDS    = 0x02U,
    PD_VEND_CMD_DISCOVER_MODES    = 0x03U,
    PD_VEND_CMD_ENTER_MODE        = 0x04U,
    PD_VEND_CMD_EXIT_MODE         = 0x05U,
    PD_VEND_CMD_ATTENTION         = 0x06U
} pd_vendor_commands_t;

/* SOP header */
typedef struct
{
    uint16_t message_type   : 5;  
    uint16_t data_role      : 1;
    uint16_t revision       : 2;
    uint16_t power_role     : 1;
    uint16_t message_id     : 3;
    uint16_t number_objects : 3;
    uint16_t extended       : 1;
} pd_sop_header_t;

/* SOP' and SOP" header */
typedef struct
{
    uint16_t message_type   : 5;  
    uint16_t reserved       : 1;
    uint16_t revision       : 2;
    uint16_t cable_plug     : 1;
    uint16_t message_id     : 3;
    uint16_t number_objects : 3;
    uint16_t extended       : 1;
} pd_sop_prime_header_t;

typedef union
{
    uint8_t raw[2];
    uint16_t all;
    pd_sop_header_t sop;
    pd_sop_prime_header_t sop_prime;
} pd_header_union_t;

/* 
    power data objects 

    Universal Serial Bus Power Delivery Specification
    
    Revision: 2
    Version: 1.3
    Release date: 2017-01-12
*/

typedef struct
{
    uint32_t max_current   : 10; /* Maximum Current in 10mA increments */
    uint32_t voltage       : 10; /* Voltage in 50mV increments */
    uint32_t peak_current  : 2;  /* Peak Current capability */
    uint32_t reserved      : 3;  /* Reserved – Shall be set to zero. */
    uint32_t dual_role     : 1;  /* Dual-Role Data */
    uint32_t usb_cooms     : 1;  /* USB Communications Capable */
    uint32_t Unconstrained : 1;  /* Unconstrained Power */
    uint32_t suspend       : 1;  /* USB Suspend Supported */
    uint32_t drp           : 1;  /* Dual-Role Power */
    uint32_t pdo_type      : 2;  /* Fixed supply == 0 */
} pd_fixed_pdo_t;

typedef struct 
{
    uint32_t max_power    : 10; /* Maximum Allowable Power in 250mW increments */
    uint32_t min_volt     : 10; /* Maximum Voltage in 50mV increments */
    uint32_t max_volt     : 10; /* Minimum Voltage in 50mV increments */
    uint32_t pdo_type     : 2;  /* Battery == 1 */
} pd_battery_pdo_t;

typedef struct 
{
    uint32_t max_current : 10; /* Maximum Current in 10mA increments */
    uint32_t min_voltage : 10; /* Minimum Voltage in 50mV increments */
    uint32_t max_voltage : 10; /* Maximum Voltage in 50mV increments */
    uint32_t pdo_type    :  2; /* Variable Supply (non-Battery) == 2 */
} pd_variable_pdo_t;

typedef struct
{
    uint32_t max_current   : 6; /* Maximum Current in 50mA increments */
    uint32_t               : 1;
    uint32_t min_voltage   : 8; /* Minimum Voltage in 100mV increments */
    uint32_t               : 1;
    uint32_t max_voltage   : 8; /* Maximum Voltage in 100mV increments */
    uint32_t               : 2;
    uint32_t power_limited : 1;
    uint32_t aug_type      : 2; /* 00b SPR Programmable Power Supply */
    uint32_t pdo_type      : 2; /* Augmented pdo == 3 */
} pd_pps_pdo_t;

typedef struct
{
    uint32_t pdp          : 8; /* PDP in 1W increments */
    uint32_t min_voltage  : 8; /* Minimum Voltage in 100mV increments */ 
    uint32_t              : 1;
    uint32_t max_voltage  : 8; /* Maximum Voltage in 100mV increments */ 
    uint32_t peak_current : 2; /* Peak Current (see Table 6.15 “EPR AVS Power Source Peak Current Capability”) */
    uint32_t aug_type     : 2; /* 01b EPR Adjustable Voltage Supply */
    uint32_t pdo_type     : 2; /* Augmented pdo == 3 */
} pd_epr_pdo_t;

typedef struct
{
    uint32_t max_current15_20v : 10; /* For 15V – 20V range: Maximum Current in 10mA units equal to the Maximum Current field of the 20V
                                        Fixed Source PDO, set to 0 if the Maximum voltage in the SPR AVS range is 15V. */
    uint32_t max_current9_15v  : 10; /* For 9V – 15V range: Maximum Current in 10mA units equal to the Maximum Current field of the 15V
                                        Fixed Source PDO */
    uint32_t                   : 6;
    uint32_t peak_current      : 2;  /* Peak Current (see Table 6.10 “Fixed Power Source Peak Current Capability”) */
    uint32_t aug_type          : 2; /* 10b SPR Adjustable Voltage Supply */
    uint32_t pdo_type          : 2; /* Augmented pdo == 3 */
} pd_avr_pdo_t;

typedef union
{    
    uint8_t raw[4];
    uint32_t raw32;
    pd_fixed_pdo_t fixed;
    pd_battery_pdo_t battery;
    pd_variable_pdo_t variable;
    pd_pps_pdo_t spr_pps; /* standard power range programmable power supply */
    pd_epr_pdo_t epr_avs; /* extended power range adjustable voltage supply */
    pd_avr_pdo_t spr_avs; /* standard power range adjustable voltage supply */
} pd_source_pdo_union_t;

typedef struct
{
    uint16_t command         : 5;
    uint16_t reserved        : 1;
    uint16_t command_type    : 2;
    uint16_t object_position : 3;
    uint16_t vdm_ver_min     : 2;
    uint16_t vdm_ver_maj     : 2;
    uint16_t stuctured       : 1;
} pd_vend_structured_t;

typedef struct
{
    uint16_t user      : 15;
    uint16_t stuctured : 1;
} pd_vend_unstructured_t;

typedef union
{
    pd_vend_structured_t structured;
    pd_vend_unstructured_t unstructured;
} pd_vend_header_lsb_t;

typedef struct
{
    pd_vend_header_lsb_t lsb;
    uint16_t vendor_id;
} pd_vendor_header_t;

typedef union
{
    pd_vendor_header_t header;
    uint8_t bytes[4];
    uint32_t raw;
} pd_vendor_header_union_t;

typedef struct
{
    uint16_t vendor_id;
    uint16_t reserved      : 10;
    uint16_t modal_support : 1;  
    uint16_t product_type  : 3;
    uint16_t usb_device    : 1;  
    uint16_t usb_host      : 1;  
} pd_vendor_id_header_t;

typedef union 
{
    pd_vendor_id_header_t header;
    uint8_t bytes[4];
} pd_vendor_id_header_union_t;

typedef struct
{
    uint16_t device;
    uint16_t product_id;
} pd_vendor_product_t;

typedef union 
{
    pd_vendor_product_t product_data;
    uint8_t bytes[4];
} pd_vendor_product_union_t;

typedef struct
{
    bool new_msg;
    uint8_t vendor_data[28];
    uint8_t no_objects;
} pd_vendor_t;

typedef struct 
{
    bool new_msg;
    uint8_t data_size;
    uint8_t data[80];
} pd_prime_t;

typedef struct
{
    pd_prime_t prime;
    pd_prime_t dbl_prime;
} pd_extras_t;

#define PD_FIXED_SUPPLY 0U
#define PD_BATTERY 1U
#define PD_VARIABLE_SUPPLY 2U
#define PD_AUGMENTED 3U
#define PD_STANDARD_POWER_PROG_PSU 0U
#define PD_EXTENDED_POWER_VOLTAGE_SUPPLY 1U
#define PD_STANDARD_POWER_VOLTAGE_SUPPLY 2U

#define PD_MAX_TX_MSG_SIZE 50 

typedef struct
{
    uint8_t tx_buffer[PD_MAX_TX_MSG_SIZE];     
    uint8_t message_length; /* length of tx data */        
    uint8_t msg_id; /* id of message, increments each transmit */
    uint8_t power_role; /* 0 sink, 1 source */
    uint8_t data_role; /* 0 UFP, 1 DFP */            
    pd_source_pdo_union_t pdos[8];                      
    uint8_t number_of_pdos;                             
    pd_control_message_type_t last_rx_control_msg_type; 
    pd_data_message_types_t last_rx_data_msg_type;
    pd_vendor_t vendor;
    pd_extras_t* extra;
} pd_state_t;

/**
 * @brief parse and decode the receive buffer
 * @param state the comms state onject
 * @param fusb the object for the fusb to use
 */
extern void fusbpd_decode( pd_state_t* state, fusb_state_t* fusb );
/**
 * @brief creat a request power message 
 * @param state the comms state object
 * @param num the index of the pdo list sent from the source
 * @param current the current required to run the device
 * @param max_current the maximum current required by the device
 */
extern void fusbpd_request_power( pd_state_t* state, uint8_t num, uint16_t current, uint16_t max_current );
/**
 * @brief create a request source capabilities message
 * @param state the comms state onject
 */            
extern void fusbpd_request_capability( pd_state_t* state );
/**
 * @brief create a vendor specific pdo message.
 * @param state the comms state object.
 * @param data buffer of data to transmit, multiple of 4. first 4 bytes must be the vendor header.
 * @param no_objects number of VDOs to transmit.  max 8 objects including vendor header
 */
extern void fusbpd_vendor_specific( pd_state_t* state, uint8_t* data, uint8_t no_objects );
/**
 * @brief create an extended message.
 * @param state the comms state object.
 * @param header pd header. 
 * @param ext_header extended header. data size used for length of message.
 * @param data buffer of data to transmit. fusb302 tx buffer is 48 bytes, 16 are needed for tx commands, length 32 max.
 */
extern void fusbpd_extended( pd_state_t* state, uint16_t header, uint16_t ext_header, uint8_t* data );
/**
 * @brief create a unchunked extended message.
 * @param state the comms state object.
 * @param header standard message header.
 * @param data buffer of data to transmit, must start with the appropriate extended header.
 * @param length data length. fusb302 tx buffer is 48 bytes, 16 are needed for tx commands, length 32 max.
 */
extern void fusbpd_prime( pd_state_t* state, uint8_t* data, uint8_t length );
/**
 * @brief create a unchunked extended message.
 * @param state the comms state object.
 * @param header standard message header.
 * @param data buffer of data to transmit.
 * @param length data length. fusb302 tx buffer is 48 bytes, 16 are needed for tx commands, length 32 max.
 */
extern void fusbpd_dbl_prime( pd_state_t* state, uint8_t* data, uint8_t length );
/**
 * @brief create a unchunked extended message.
 * @param state the comms state object.
 */
extern void fusbpd_vendor_id( pd_state_t* state );
/**
 * @brief create a reject command.
 * @param state the comms state object.
 */
extern void fusbpd_reject( pd_state_t* state );

#endif /* FUSB302B_PD_H */
