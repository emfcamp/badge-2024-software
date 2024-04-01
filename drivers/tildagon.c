#include "tildagon.h"

static tca9548a_i2c_mux_t tildagon_i2c_mux;

const tca9548a_i2c_mux_t *tildagon_get_i2c_mux() {
  if(tildagon_i2c_mux.addr == 0) {
    tildagon_i2c_mux.mtx = xSemaphoreCreateBinary();
    if (tildagon_i2c_mux.mtx == NULL) {
      return NULL;
    }
    xSemaphoreGive(&tildagon_i2c_mux.mtx);
    tildagon_i2c_mux.addr = 0x77;
  }
  return &tildagon_i2c_mux;
}