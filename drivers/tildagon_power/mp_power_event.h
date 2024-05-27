
#ifndef MP_POWER_EVENT_H
#define MP_POWER_EVENT_H

#include "stdint.h"

typedef enum 
{
    MP_POWER_EVENT_CHARGE,           
    MP_POWER_EVENT_FAULT,            
    MP_POWER_EVENT_HOST_ATTACH,      
    MP_POWER_EVENT_HOST_DETACH,      
    MP_POWER_EVENT_DEVICE_ATTACH,    
    MP_POWER_EVENT_DEVICE_DETACH,    
    MP_POWER_EVENT_LANYARD_ATTACH,   
    MP_POWER_EVENT_LANYARD_DETACH,
    MP_POWER_EVENT_MAX            
} mp_power_event_t;

extern void push_event( mp_power_event_t event );

#endif
