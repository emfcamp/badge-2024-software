
#ifndef MP_FRONTBOARD_H
#define MP_FRONTBOARD_H

#include <stdint.h>

#define MP_TOUCH_EVENT_1 0         
#define MP_TOUCH_EVENT_2 1           
#define MP_TOUCH_EVENT_3 2     
#define MP_TOUCH_EVENT_4 3     
#define MP_TOUCH_EVENT_5 4
#define MP_TOUCH_EVENT_6 5   
#define MP_TOUCH_EVENT_7 6  
#define MP_TOUCH_EVENT_8 7
#define MP_TOUCH_EVENT_9 8
#define MP_TOUCH_EVENT_10 9
#define MP_TOUCH_EVENT_11 10
#define MP_TOUCH_EVENT_12 11
#define MP_PROX_EVENT_1 12
#define MP_PROX_EVENT_2 13
#define MP_FB_EVENT_MAX 14   

#define MP_FB_RISING_EDGE 0
#define MP_FB_FALLING_EDGE 1

extern void mp_frontboard2026_push_event( uint8_t event, uint8_t trigger );

#endif
