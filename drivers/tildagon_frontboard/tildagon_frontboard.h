#ifndef TILDAGON_FRONTBOARD_H
#define TILDAGON_FRONTBOARD_H

extern void tildagon_frontboard_2026_init( void );
extern uint16_t tildagon_frontboard_get_model( void );
extern void cy8cmbrx_cb( void* args ,uint8_t event );
#endif