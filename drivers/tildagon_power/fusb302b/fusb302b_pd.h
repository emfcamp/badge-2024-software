
#ifndef FUSB302B_PD_H
#define FUSB302B_PD_H

#include <stdint.h>
#include "fusb302b.h"

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
    pd_sop_header_t sop;
    pd_sop_prime_header_t sop_prime;
} pd_header_union_t;

/* power data objects */

typedef struct
{
    uint32_t max_current   : 10; /* Maximum Current in 10mA units */
    uint32_t voltage       : 10; /* Voltage in 50mV units */
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
    uint32_t max_power    : 10; /* Maximum Allowable Power in 250mW units */
    uint32_t min_volt     : 10; /* Maximum Voltage in 50mV units */
    uint32_t max_volt     : 10; /* Minimum Voltage in 50mV units */
    uint32_t pdo_type     : 2;  /* Battery == 1 */
} pd_battery_pdo_t;

typedef struct 
{
    uint32_t max_current : 10; /* Maximum Current in 10mA units */
    uint32_t min_voltage : 10; /* Minimum Voltage in 50mV units */
    uint32_t max_voltage : 10; /* Maximum Voltage in 50mV units */
    uint32_t pdo_type     : 2; /* Variable Supply (non-Battery) == 2 */
} pd_variable_pdo_t;

typedef union
{    
    uint8_t raw[4];
    uint32_t raw32;
    pd_fixed_pdo_t fixed;
    pd_battery_pdo_t battery;
    pd_variable_pdo_t variable;
} pd_source_pdo_union_t;

typedef struct 
{
    uint32_t min_current         : 10;
    uint32_t current             : 10;
    uint32_t reserved            : 2;
    uint32_t epr_cap             : 1;
    uint32_t uem_suspend         : 1;
    uint32_t no_suspend          : 1;
    uint32_t usb_comms           : 1;
    uint32_t capability_mismatch : 1;
    uint32_t give_back           : 1;
    uint32_t position            : 1;
} pd_request_pdo_t;

typedef union 
{
    uint32_t raw;
    pd_request_pdo_t bits;
} pd_request_pdo_union_t;

#define PD_FIXED_SUPPLY 0U
#define PD_BATTERY 1U
#define PD_VARIABLE_SUPPLY 2U
#define PD_MAX_TX_MSG_SIZE 50 
#define PD_VENDOR_ID 0xCDCD

typedef struct
{
    uint8_t tx_buffer[PD_MAX_TX_MSG_SIZE];              
    uint8_t message_length;                             
    uint8_t msg_id;                                     
    uint8_t power_role;                                 
    uint8_t data_role;                                  
    pd_header_union_t last_rx_header;                   
    pd_source_pdo_union_t pdos[8];                      
    uint8_t number_of_pdos;                             
    pd_control_message_type_t last_rx_control_msg_type; 
    pd_data_message_types_t last_rx_data_msg_type;      
    uint8_t badge_id[8];
    uint8_t rx_badge_id[8];            
} pd_state_t;

/**
 * @brief parse and decode the receive buffer
 * @param state the comms state onject
 * @param fusb the object for the fusb to use
 */
extern void fusbpd_decode( pd_state_t* state, fusb_state_t* fusb );
/**
 * @brief creat a request power message 
 * @param state the comms state onject
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
 * @brief create a vendor specific pdo message with the esp32 unique id
 * @param state the comms state onject
 */
extern void fusbpd_vendor_specific( pd_state_t* state );

#endif /* FUSB302B_PD_H */
