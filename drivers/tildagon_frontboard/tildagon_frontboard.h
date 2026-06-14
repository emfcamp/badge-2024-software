#ifndef TILDAGON_FRONTBOARD_H
#define TILDAGON_FRONTBOARD_H

extern void tildagon_frontboard_init( uint16_t board_id );
extern uint16_t tildagon_frontboard_get_model( void );
extern void cy8cmbrx_cb( void* args ,uint8_t event );
#endif