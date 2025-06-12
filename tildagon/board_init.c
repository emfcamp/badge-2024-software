#include "st3m_imu.h"

#include "tildagon_power.h"

// This is the default startup handler for ESP32, does VFS and stuff
void boardctrl_startup(void);

// TODO put this in a header and get it in the include path somehow
void tildagon_usb_init(void);

// TODO put this in a header and get it in the include path somehow
// it exists in tildagon_i2c.h but including it here throws an error 
// (some #define not set correctly?)
void tildagon_i2c_init(void);

void tildagon_pins_init(void);

void tildagon_startup(void) {
    // call the micropy default startup - does VFS init on ESP32
    boardctrl_startup();
    
    tildagon_i2c_init();
    
    tildagon_pins_init();
    
    tildagon_power_init();
	
    tildagon_usb_init();

    
    st3m_imu_init();

}
