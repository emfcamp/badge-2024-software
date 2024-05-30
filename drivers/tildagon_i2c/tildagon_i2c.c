/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2019 Damien P. George
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

 /**
  * Taken partly from ports/esp32/machine_i2c.c
 */

#include "py/runtime.h"
#include "py/mphal.h"
#include "py/mperrno.h"
#include "extmod/modmachine.h"

#include "driver/i2c.h"
#include "hal/i2c_ll.h"
#include "driver/gpio.h"

#include "tildagon_i2c.h"


#if MICROPY_PY_TILDAGON_I2C

#define I2C_DEFAULT_TIMEOUT_US (50000) // 50ms

#define MP_I2C_MUX_PORT_MIN (0)
#define MP_I2C_MUX_PORT_MAX (7)



static tildagon_mux_i2c_obj_t tildagon_mux_i2c_obj[8];

static tca9548a_i2c_mux_t tildagon_i2c_mux;

tildagon_mux_i2c_obj_t* tildagon_get_mux_obj( uint8_t port )
{
    if ( tildagon_mux_i2c_obj[port].base.type == NULL ) 
    {
        // Created for the first time
        tildagon_mux_i2c_obj[port].base.type = &machine_i2c_type;
        tildagon_mux_i2c_obj[port].mux = tildagon_get_i2c_mux();
        tildagon_mux_i2c_obj[port].port = port;
    }
    return &tildagon_mux_i2c_obj[port];
}

const tca9548a_i2c_mux_t *tildagon_get_i2c_mux() {
    return &tildagon_i2c_mux;
}

void tildagon_i2c_init() {
    tildagon_i2c_mux.mtx = xSemaphoreCreateMutex();
    tildagon_i2c_mux.addr = 0x77;
    tildagon_i2c_mux.active_port = -1;
    
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = TILDAGON_HOST_I2C_SDA,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_io_num = TILDAGON_HOST_I2C_SCL,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = TILDAGON_HOST_I2C_FREQ,
    };
    i2c_param_config(TILDAGON_HOST_I2C_PORT, &conf);
    int timeout = I2C_SCLK_FREQ / 1000000 * TILDAGON_HOST_I2C_TIMEOUT;
    i2c_set_timeout(TILDAGON_HOST_I2C_PORT, (timeout > I2C_LL_MAX_TIMEOUT) ? I2C_LL_MAX_TIMEOUT : timeout);
    i2c_driver_install(TILDAGON_HOST_I2C_PORT, I2C_MODE_MASTER, 0, 0, 0);
    // reset I2C
    gpio_set_direction(GPIO_NUM_9, GPIO_MODE_OUTPUT);
    gpio_set_level(GPIO_NUM_9, 1);
}


int tildagon_mux_i2c_transaction(tildagon_mux_i2c_obj_t *self, uint16_t addr, size_t n, mp_machine_i2c_buf_t *bufs, unsigned int flags) {
   
    int data_len = 0;
    i2c_cmd_handle_t cmd = i2c_cmd_link_create();

    if (flags & MP_MACHINE_I2C_FLAG_WRITE1) {
        i2c_master_start(cmd);
        i2c_master_write_byte(cmd, addr << 1, true);
        i2c_master_write(cmd, bufs->buf, bufs->len, true);
        data_len += bufs->len;
        --n;
        ++bufs;
    }

    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, addr << 1 | (flags & MP_MACHINE_I2C_FLAG_READ), true);

    for (; n--; ++bufs) {
        if (flags & MP_MACHINE_I2C_FLAG_READ) {
            i2c_master_read(cmd, bufs->buf, bufs->len, n == 0 ? I2C_MASTER_LAST_NACK : I2C_MASTER_ACK);
        } else {
            if (bufs->len != 0) {
                i2c_master_write(cmd, bufs->buf, bufs->len, true);
            }
        }
        data_len += bufs->len;
    }

    if (flags & MP_MACHINE_I2C_FLAG_STOP) {
        i2c_master_stop(cmd);
    }

    // TODO proper timeout
    esp_err_t err = tca9548a_master_cmd_begin(self->mux, self->port, cmd, 100 * (3 + data_len) / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(cmd);

    if (err == ESP_FAIL) {
        return -MP_ENODEV;
    } else if (err == ESP_ERR_TIMEOUT) {
        return -MP_ETIMEDOUT;
    } else if (err != ESP_OK) {
        return -abs(err);
    }

    return data_len;
}

int tildagon_mux_i2c_transfer(mp_obj_base_t *self_in, uint16_t addr, size_t n, mp_machine_i2c_buf_t *bufs, unsigned int flags) {
    tildagon_mux_i2c_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (addr == self->mux->addr) {
        return -MP_ENODEV;
    }
    
    return tildagon_mux_i2c_transaction( self, addr, n, bufs, flags);
}

/******************************************************************************/
// MicroPython bindings for machine API

static void tildagon_mux_i2c_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    tildagon_mux_i2c_obj_t *self = MP_OBJ_TO_PTR(self_in);
    int h, l;
    i2c_get_period(self->mux->port, &h, &l);
    mp_printf(print, "I2C(%u, freq=%u)",
        self->port, I2C_SCLK_FREQ / (h + l));
}

mp_obj_t tildagon_mux_i2c_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    MP_MACHINE_I2C_CHECK_FOR_LEGACY_SOFTI2C_CONSTRUCTION(n_args, n_kw, all_args);

    // Parse args
    enum { ARG_id };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_id, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    // Get I2C bus
    mp_int_t i2c_id = mp_obj_get_int(args[ARG_id].u_obj);
    if (!(MP_I2C_MUX_PORT_MIN <= i2c_id && i2c_id <= MP_I2C_MUX_PORT_MAX)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("I2C(%d) doesn't exist"), i2c_id);
    }

    // Get static peripheral object
    tildagon_mux_i2c_obj_t *self = (tildagon_mux_i2c_obj_t *)&tildagon_mux_i2c_obj[i2c_id];

    if (self->base.type == NULL) {
        // Created for the first time, set default pins
        self->base.type = &machine_i2c_type;
        self->mux = tildagon_get_i2c_mux();
        self->port = i2c_id;
    }

    return MP_OBJ_FROM_PTR(self);
}

static const mp_machine_i2c_p_t tildagon_mux_i2c_p = {
    .transfer_supports_write1 = true,
    .transfer = tildagon_mux_i2c_transfer,
};

MP_DEFINE_CONST_OBJ_TYPE(
    machine_i2c_type,
    MP_QSTR_I2C,
    MP_TYPE_FLAG_NONE,
    make_new, tildagon_mux_i2c_make_new,
    print, tildagon_mux_i2c_print,
    protocol, &tildagon_mux_i2c_p,
    locals_dict, &mp_machine_i2c_locals_dict
    );

#endif
