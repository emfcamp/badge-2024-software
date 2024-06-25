/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * Development of the code in this file was sponsored by Microbric Pty Ltd
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2016-2023 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/rtc_io.h"
#include "hal/gpio_ll.h"

#include "py/runtime.h"
#include "py/mphal.h"
#include "extmod/modmachine.h"
#include "extmod/virtpin.h"
#include "mphalport.h"
#include "modmachine.h"
#include "tildagon_pin.h"
#include "machine_rtc.h"
#include "modesp32.h"
#include "pins.h"

#include "py/mpprint.h"

// Return the tildagon_pin_obj_t pointer corresponding to a tildagon_pin_irq_obj_t pointer.
#define PIN_OBJ_PTR_FROM_IRQ_OBJ_PTR(self) ((tildagon_pin_obj_t *)((uintptr_t)(self) - offsetof(tildagon_pin_obj_t, irq)))

#define PIN_OBJ_PTR_DEVICE(self) (&ext_pin[PIN_OBJ_PTR_INDEX(self)/16])
#define PIN_OBJ_PTR_PORTPIN(self) (PIN_OBJ_PTR_INDEX(self)%16)
#define PORTPIN_IS_VALID_LED(pin) (0 <= pin && pin < 16)
#define PIN_OBJ_PTR_INDEX(self) ((self) - tildagon_pin_obj_table)
// this is outside of machine.Pins defines
#define EGPIO_MODE_PWM 8

aw9523b_device_t ext_pin[3] = {
    {
        .i2c_port = TILDAGON_SYS_I2C_PORT,
        .i2c_addr = 0x58,
    },
    {
        .i2c_port = TILDAGON_SYS_I2C_PORT,
        .i2c_addr = 0x59,
    },
    {
        .i2c_port = TILDAGON_SYS_I2C_PORT,
        .i2c_addr = 0x5a,
    }
};


static const tildagon_pin_obj_t *tildagon_pin_find_named(const mp_obj_dict_t *named_pins, mp_obj_t name) {
    const mp_map_t *named_map = &named_pins->map;
    mp_map_elem_t *named_elem = mp_map_lookup((mp_map_t *)named_map, name, MP_MAP_LOOKUP);
    if (named_elem != NULL && named_elem->value != NULL) {
        return MP_OBJ_TO_PTR(named_elem->value);
    }
    return NULL;
}

void tildagon_pins_init(void) {
    static bool did_install = false;
    if (!did_install) {
        for (int i = 0; i < 3; i++){
            ext_pin[i].mux = tildagon_get_i2c_mux();
            aw9523b_init(&ext_pin[i]);
        }
        // setup outputs mux [2] 2, 4 and 5. 5v sw, usb mux and led sw 
        aw9523b_pin_set_direction( &ext_pin[2], 2,  false );
        aw9523b_pin_set_output( &ext_pin[2], 2,  false );
        aw9523b_pin_set_direction( &ext_pin[2], 4,  false );
        aw9523b_pin_set_output( &ext_pin[2], 4,  false );
        aw9523b_pin_set_direction( &ext_pin[2], 5,  false );
        aw9523b_pin_set_output( &ext_pin[2], 5,  false );
        did_install = true;
    }
    memset(&MP_STATE_PORT(tildagon_pin_irq_handler[0]), 0, sizeof(MP_STATE_PORT(tildagon_pin_irq_handler)));
}

static void tildagon_pin_isr_handler(void *arg) {
    tildagon_pin_obj_t *self = arg;
    mp_obj_t handler = MP_STATE_PORT(tildagon_pin_irq_handler)[PIN_OBJ_PTR_INDEX(self)];
    mp_sched_schedule(handler, MP_OBJ_FROM_PTR(self));
    mp_hal_wake_main_task_from_isr();
}

static const tildagon_pin_obj_t *tildagon_pin_find(mp_obj_t pin_in) {
    if (mp_obj_is_type(pin_in, &tildagon_pin_type)) {
        return pin_in;
    }

    // Try to find the pin via tuple index into the array of all pins.
    if (mp_obj_is_exact_type(pin_in, &mp_type_tuple)) {
        mp_obj_t *items;
        size_t len;
        mp_obj_tuple_get(pin_in, &len, &items);
        if (len == 2) {
            mp_int_t bank = mp_obj_get_int(items[0]);
            mp_int_t index = mp_obj_get_int(items[1]);
            if (0 <= bank && bank < 3 && 0 <= index && index < 16) {
                const tildagon_pin_obj_t *self = &tildagon_pin_obj_table[bank*16 + index];
                if (self->base.type != NULL) {
                    return self;
                }
            }
        }
    }

    // Try to find the pin in the board pins dict.
    if (mp_obj_is_str(pin_in)) {
        const tildagon_pin_obj_t *self = tildagon_pin_find_named(&tildagon_pin_board_pins_locals_dict, pin_in);
        if (self && self->base.type != NULL) {
            return self;
        }
    }

    mp_raise_ValueError(MP_ERROR_TEXT("invalid LS pin"));
}

gpio_num_t tildagon_pin_get_id(mp_obj_t pin_in) {
    const tildagon_pin_obj_t *self = tildagon_pin_find(pin_in);
    return PIN_OBJ_PTR_INDEX(self);
}

static void tildagon_pin_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    tildagon_pin_obj_t *self = self_in;
    mp_printf(print, "ePin((%u, %u))", (PIN_OBJ_PTR_INDEX(self)/16), (PIN_OBJ_PTR_INDEX(self)%16));
}

// pin.init(mode=None, value)
static mp_obj_t tildagon_pin_obj_init_helper(const tildagon_pin_obj_t *self, size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_mode, ARG_value };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_mode, MP_ARG_OBJ, {.u_obj = mp_const_none}},
        { MP_QSTR_value, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL}},
    };

    // parse args
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    aw9523b_device_t *dev = PIN_OBJ_PTR_DEVICE(self);
    aw9523b_pin_t pin = PIN_OBJ_PTR_PORTPIN(self);

    // set initial value (do this before configuring mode/pull)
    if (args[ARG_value].u_obj != MP_OBJ_NULL) {
        aw9523b_pin_set_output(dev, pin, mp_obj_is_true(args[ARG_value].u_obj));
    }

    // configure mode
    if (args[ARG_mode].u_obj != mp_const_none) {
        mp_int_t pin_io_mode = mp_obj_get_int(args[ARG_mode].u_obj);
        if ( pin_io_mode == EGPIO_MODE_PWM )
        {
            aw9523b_pin_set_drive( dev, pin, 0 );
            aw9523b_pin_set_mode(dev, pin, AW9523B_PIN_MODE_LED);
        }
        else
        {
            // configure the pin for gpio
            aw9523b_pin_set_mode(dev, pin, AW9523B_PIN_MODE_GPIO);
         
            if ( pin_io_mode == GPIO_MODE_INPUT_OUTPUT )
            {
                aw9523b_pin_set_direction(dev, pin, 0);
            }
            else
            {
                aw9523b_pin_set_direction(dev, pin, 1);
            }
        }
    }

    return mp_const_none;
}

// constructor(id, ...)
mp_obj_t mp_tildagon_pin_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 1, MP_OBJ_FUN_ARGS_MAX, true);

    // get the wanted pin object
    const tildagon_pin_obj_t *self = tildagon_pin_find(args[0]);

    if (n_args > 1 || n_kw > 0) {
        // pin mode given, so configure this GPIO
        mp_map_t kw_args;
        mp_map_init_fixed_table(&kw_args, n_kw, args + n_args);
        tildagon_pin_obj_init_helper(self, n_args - 1, args + 1, &kw_args);
    }

    return MP_OBJ_FROM_PTR(self);
}

// fast method for getting/setting pin value
static mp_obj_t tildagon_pin_call(mp_obj_t self_in, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 1, false);
    tildagon_pin_obj_t *self = self_in;
    aw9523b_device_t *dev = PIN_OBJ_PTR_DEVICE(self);
    aw9523b_pin_t pin = PIN_OBJ_PTR_PORTPIN(self);
    if (n_args == 0) {
        // get pin
        return MP_OBJ_NEW_SMALL_INT(aw9523b_pin_get_input(dev, pin));
    } else {
        // set pin
        aw9523b_pin_set_output(dev, pin, mp_obj_is_true(args[0]));
        return mp_const_none;
    }
}

// pin.init(mode, pull)
static mp_obj_t tildagon_pin_obj_init(size_t n_args, const mp_obj_t *args, mp_map_t *kw_args) {
    return tildagon_pin_obj_init_helper(args[0], n_args - 1, args + 1, kw_args);
}
MP_DEFINE_CONST_FUN_OBJ_KW(tildagon_pin_init_obj, 1, tildagon_pin_obj_init);

// pin.value([value])
static mp_obj_t tildagon_pin_value(size_t n_args, const mp_obj_t *args) {
    return tildagon_pin_call(args[0], n_args - 1, 0, args + 1);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(tildagon_pin_value_obj, 1, 2, tildagon_pin_value);

// pin.off()
static mp_obj_t tildagon_pin_off(mp_obj_t self_in) {
    tildagon_pin_obj_t *self = MP_OBJ_TO_PTR(self_in);
    aw9523b_device_t *dev = PIN_OBJ_PTR_DEVICE(self);
    aw9523b_pin_t pin = PIN_OBJ_PTR_PORTPIN(self);
    aw9523b_pin_set_output(dev, pin, 0);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_pin_off_obj, tildagon_pin_off);

// pin.on()
static mp_obj_t tildagon_pin_on(mp_obj_t self_in) {
    tildagon_pin_obj_t *self = MP_OBJ_TO_PTR(self_in);
    aw9523b_device_t *dev = PIN_OBJ_PTR_DEVICE(self);
    aw9523b_pin_t pin = PIN_OBJ_PTR_PORTPIN(self);
    aw9523b_pin_set_output(dev, pin, 1);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(tildagon_pin_on_obj, tildagon_pin_on);

// pin.irq(handler=None, trigger=IRQ_FALLING|IRQ_RISING)
static mp_obj_t tildagon_pin_irq(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_handler, ARG_trigger };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_handler, MP_ARG_OBJ, {.u_obj = mp_const_none} },
        { MP_QSTR_trigger, MP_ARG_INT, {.u_int = GPIO_INTR_POSEDGE | GPIO_INTR_NEGEDGE} },
    };
    tildagon_pin_obj_t *self = MP_OBJ_TO_PTR(pos_args[0]);
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args - 1, pos_args + 1, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (n_args > 1 || kw_args->used != 0) {
        // configure irq
        aw9523b_device_t *dev = PIN_OBJ_PTR_DEVICE(self);
        aw9523b_pin_t pin = PIN_OBJ_PTR_PORTPIN(self);
        uint8_t index = PIN_OBJ_PTR_INDEX(self);
        mp_obj_t handler = args[ARG_handler].u_obj;
        //mp_obj_t trigger = args[ARG_trigger].u_obj;

        if (handler != mp_const_none) {
            aw9523b_irq_register(dev, pin, tildagon_pin_isr_handler, self);
            aw9523b_irq_enable(dev, pin);
        } else {
            aw9523b_irq_unregister(dev, pin);
            aw9523b_irq_disable(dev, pin);
            handler = MP_OBJ_NULL;
        }
        MP_STATE_PORT(tildagon_pin_irq_handler)[index] = handler;

    }

    // return the irq object
    return MP_OBJ_FROM_PTR(&self->irq);
}
//static MP_DEFINE_CONST_FUN_OBJ_KW(tildagon_pin_irq_obj, 1, tildagon_pin_irq);

static mp_obj_t tildagon_pin_duty(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    enum { ARG_duty };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_duty, MP_ARG_OBJ, {.u_obj = mp_const_none} },    
    };
    tildagon_pin_obj_t *self = MP_OBJ_TO_PTR(pos_args[0]);
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args - 1, pos_args + 1, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    if (n_args > 1 || kw_args->used != 0) {
          // configure irq
        aw9523b_device_t *dev = PIN_OBJ_PTR_DEVICE(self);
        aw9523b_pin_t pin = PIN_OBJ_PTR_PORTPIN(self);
        mp_obj_t mp_duty = args[ARG_duty].u_obj;
        uint8_t duty = mp_obj_get_int(mp_duty);
        aw9523b_pin_set_drive( dev, pin, duty );
    }
    
    return mp_const_none;
}

static MP_DEFINE_CONST_FUN_OBJ_KW(tildagon_pin_duty_obj, 1, tildagon_pin_duty);

MP_DEFINE_CONST_OBJ_TYPE(
    tildagon_pin_board_pins_obj_type,
    MP_QSTR_board,
    MP_TYPE_FLAG_NONE,
    locals_dict, &tildagon_pin_board_pins_locals_dict
    );

static const mp_rom_map_elem_t tildagon_pin_locals_dict_table[] = {
    // instance methods
    { MP_ROM_QSTR(MP_QSTR___init__), MP_ROM_PTR(&tildagon_pin_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&tildagon_pin_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_value), MP_ROM_PTR(&tildagon_pin_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_off), MP_ROM_PTR(&tildagon_pin_off_obj) },
    { MP_ROM_QSTR(MP_QSTR_on), MP_ROM_PTR(&tildagon_pin_on_obj) },
    //todo reinstate once triggers can be split into rising/falling edge
    //{ MP_ROM_QSTR(MP_QSTR_irq), MP_ROM_PTR(&tildagon_pin_irq_obj) },
    { MP_ROM_QSTR(MP_QSTR_duty), MP_ROM_PTR(&tildagon_pin_duty_obj) },

    // class attributes
    { MP_ROM_QSTR(MP_QSTR_board), MP_ROM_PTR(&tildagon_pin_board_pins_obj_type) },

    // class constants
    { MP_ROM_QSTR(MP_QSTR_IN), MP_ROM_INT(GPIO_MODE_INPUT) },
    { MP_ROM_QSTR(MP_QSTR_OUT), MP_ROM_INT(GPIO_MODE_INPUT_OUTPUT) },
    { MP_ROM_QSTR(MP_QSTR_PWM), MP_ROM_INT(EGPIO_MODE_PWM) },
    //{ MP_ROM_QSTR(MP_QSTR_IRQ_RISING), MP_ROM_INT(GPIO_INTR_POSEDGE) },
    //{ MP_ROM_QSTR(MP_QSTR_IRQ_FALLING), MP_ROM_INT(GPIO_INTR_NEGEDGE) },
};

static mp_uint_t tildagon_pin_ioctl(mp_obj_t self_in, mp_uint_t request, uintptr_t arg, int *errcode) {
    (void)errcode;
    tildagon_pin_obj_t *self = self_in;
    aw9523b_device_t *dev = PIN_OBJ_PTR_DEVICE(self);
    aw9523b_pin_t pin = PIN_OBJ_PTR_PORTPIN(self);

    switch (request) {
        case MP_PIN_READ: {
            return aw9523b_pin_get_input(dev, pin);
        }
        case MP_PIN_WRITE: {
            aw9523b_pin_set_output(dev, pin, arg);
            return 0;
        }
    }
    return -1;
}

static MP_DEFINE_CONST_DICT(tildagon_pin_locals_dict, tildagon_pin_locals_dict_table);

static const mp_pin_p_t tildagon_pin_pin_p = {
    .ioctl = tildagon_pin_ioctl,
};

MP_DEFINE_CONST_OBJ_TYPE(
    tildagon_pin_type,
    MP_QSTR_ePin,
    MP_TYPE_FLAG_NONE,
    make_new, mp_tildagon_pin_make_new,
    print, tildagon_pin_print,
    call, tildagon_pin_call,
    protocol, &tildagon_pin_pin_p,
    locals_dict, &tildagon_pin_locals_dict
    );

/******************************************************************************/
// Pin IRQ object

static mp_obj_t tildagon_pin_irq_call(mp_obj_t self_in, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    tildagon_pin_irq_obj_t *self = self_in;
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    tildagon_pin_isr_handler((void *)PIN_OBJ_PTR_FROM_IRQ_OBJ_PTR(self));
    return mp_const_none;
}

static mp_obj_t tildagon_pin_irq_trigger(size_t n_args, const mp_obj_t *args) {
    tildagon_pin_irq_obj_t *self = args[0];
    gpio_num_t index = PIN_OBJ_PTR_INDEX(PIN_OBJ_PTR_FROM_IRQ_OBJ_PTR(self));
    uint32_t orig_trig = GPIO.pin[index].int_type;
    if (n_args == 2) {
        // set trigger
        gpio_set_intr_type(index, mp_obj_get_int(args[1]));
    }
    // return original trigger value
    return MP_OBJ_NEW_SMALL_INT(orig_trig);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(tildagon_pin_irq_trigger_obj, 1, 2, tildagon_pin_irq_trigger);

static const mp_rom_map_elem_t tildagon_pin_irq_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_trigger), MP_ROM_PTR(&tildagon_pin_irq_trigger_obj) },
};
static MP_DEFINE_CONST_DICT(tildagon_pin_irq_locals_dict, tildagon_pin_irq_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    tildagon_pin_irq_type,
    MP_QSTR_IRQ,
    MP_TYPE_FLAG_NONE,
    call, tildagon_pin_irq_call,
    locals_dict, &tildagon_pin_irq_locals_dict
    );

MP_REGISTER_ROOT_POINTER(mp_obj_t tildagon_pin_irq_handler[GPIO_PIN_COUNT]);
