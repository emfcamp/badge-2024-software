#ifndef _MICROPY_PY_TILDAGON_PIN
#define _MICROPY_PY_TILDAGON_PIN

#include "pins.h"
#include "aw9523b.h"


typedef struct _tildagon_pin_irq_obj_t {
    mp_obj_base_t base;
} tildagon_pin_irq_obj_t;

typedef struct _tildagon_pin_obj_t {
    mp_obj_base_t base;
    tildagon_pin_irq_obj_t irq;
} tildagon_pin_obj_t;

extern aw9523b_device_t ext_pin[3];
extern const mp_obj_type_t tildagon_pin_irq_type;
extern const mp_obj_type_t tildagon_pin_type;

extern const tildagon_pin_obj_t tildagon_pin_obj_table[GPIO_EXT_NUM_MAX];

extern const mp_obj_dict_t tildagon_pin_board_pins_locals_dict;

void tildagon_pins_init();

#endif // _MICROPY_PY_TILDAGON_PIN
