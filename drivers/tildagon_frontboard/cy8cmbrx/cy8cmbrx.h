#ifndef CY8CMBRX_H
#define CY8CMBRX_H


#include "tildagon_i2c.h"

#define CY8CMBRX_ADDRESS 0x37U
#define CY8CMBRX_BUTTON_STAT_ADR 0xAAU
#define CY8CMBRX_CTRL_CMD_ADR 0x86U

#define CY8CMBRX_CMD_CMP_CRC_SAVE 0x02U
#define CY8CMBRX_CMD_CALC_CRC 0x03U
#define CY8CMBRX_CMD_LOW_POWER 0x07U
#define CY8CMBRX_CMD_RESET_LATCH 0x08U
#define CY8CMBRX_CMD_RESET_PS0_FILTER 0x09U
#define CY8CMBRX_CMD_RESET_PS1_FILTER 0x0AU
#define CY8CMBRX_CMD_RESET 0xFFU

#define CY8CMBRX_CMD_ERR_OK 0x00U
#define CY8CMBRX_CMD_ERR_SAVE_FAILED 0x0DU
#define CY8CMBRX_CMD_ERR_CRC_MISMATCH 0xFEU
#define CY8CMBRX_CMD_ERR_INVALID_CMD 0xFFU

typedef enum
{
    CY8CMBRX_NO_CHANGE,
    CY8CMBRX_RISING_EDGE,
    CY8CMBRX_FALLING_EDGE,
    CY8CMBRX_PULSE
} cy8cmbrx_event_t;

typedef struct 
{
    cy8cmbrx_event_t buttons[16];
    cy8cmbrx_event_t prox[2];
} cy8cmbrx_status_t;


extern void cy8cmbrx_init( tildagon_mux_i2c_obj_t* mux_port);
extern cy8cmbrx_status_t cy8cmbrx_run( void );
extern void cy8cmbrx_read_differences( uint16_t buffer[16] );

#endif
