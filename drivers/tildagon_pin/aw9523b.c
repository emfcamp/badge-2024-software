#include "aw9523b.h"
#include <assert.h>

#include "tildagon_i2c.h"

#define READ ( MP_MACHINE_I2C_FLAG_WRITE1 | MP_MACHINE_I2C_FLAG_READ | MP_MACHINE_I2C_FLAG_STOP )
#define WRITE MP_MACHINE_I2C_FLAG_STOP

static void aw9523b_check_valid_pin(aw9523b_pin_t pin) {
    assert(pin <= 15);
}

static uint8_t aw9523b_portnum(aw9523b_pin_t pin) {
    return pin / 8;
}
static uint8_t aw9523b_portpin(aw9523b_pin_t pin) {
    return pin % 8;
}

static esp_err_t aw9523b_readregs(aw9523b_device_t *dev, uint8_t reg, uint8_t *regs, size_t nregs) {
    
    tildagon_mux_i2c_obj_t *mux = tildagon_get_mux_obj(7);
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &reg },
                                       { .len = nregs, .buf = regs } };
    return tildagon_mux_i2c_transaction(mux, dev->i2c_addr, 2, (mp_machine_i2c_buf_t*)&buffer, READ);
}

static esp_err_t aw9523b_writeregs(aw9523b_device_t *dev, uint8_t reg, const uint8_t *regs, size_t nregs) {
    uint8_t buf[nregs+1];
    buf[0] = reg;
    memcpy(buf+1, regs, nregs);
    tildagon_mux_i2c_obj_t *mux = tildagon_get_mux_obj(7);
    mp_machine_i2c_buf_t buffer[1] = { { .len = nregs+1, .buf = buf } };
    return tildagon_mux_i2c_transaction(mux, dev->i2c_addr, 1, (mp_machine_i2c_buf_t*)&buffer, WRITE);
}

void aw9523b_init(aw9523b_device_t *dev) 
{
    aw9523b_writeregs(dev, 0x7F, (const uint8_t*)"\x00", 2);
    aw9523b_writeregs(dev, 0x06, (const uint8_t*)"\xff\xff", 2);
    aw9523b_writeregs(dev, 0x04, (const uint8_t*)"\xff\xff", 2);
    aw9523b_writeregs(dev, 0x11, (const uint8_t*)"\x10", 1);
    aw9523b_writeregs(dev, 0x20, (const uint8_t*)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 16);
    dev->irq_enables[0] = 0xFFU;
    dev->irq_enables[1] = 0xFFU;
    aw9523b_pin_get_input(dev, 0);
    aw9523b_pin_get_input(dev, 8);
}


bool aw9523b_pin_get_input(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    uint8_t reg = 0x00 + port;
    uint8_t reg_val = 0;
    esp_err_t err = aw9523b_readregs(dev, reg, &reg_val, 1);
    if (err < 0) {
        return false;
    }
    dev->last_input_values[port] = reg_val;
    bool pin_val = (reg_val & pin_mask) != 0;
    return pin_val;
}

bool aw9523b_pin_get_output(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    uint8_t reg = 0x02 + port;
    uint8_t reg_val = 0;
    esp_err_t err = aw9523b_readregs(dev, reg, &reg_val, 1);
    if (err < 0) {
        return false;
    }
    bool pin_val = (reg_val & pin_mask) != 0;
    return pin_val;
}

void aw9523b_pin_set_output(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_state_t state) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    uint8_t reg = 0x02 + port;
    uint8_t reg_val = 0;
    esp_err_t err = aw9523b_readregs(dev, reg, &reg_val, 1);
    if (err < 0) {
        return;
    }
    if (state) {
        reg_val |= pin_mask;
    } else {
        reg_val &= ~pin_mask;
    }
    err = aw9523b_writeregs(dev, reg, &reg_val, 1);
}

bool aw9523b_pin_get_direction(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    uint8_t reg = 0x04 + port;
    uint8_t reg_val = 0;
    esp_err_t err = aw9523b_readregs(dev, reg, &reg_val, 1);
    if (err < 0) {
        return false;
    }
    bool pin_val = (reg_val & pin_mask) != 0;
    return pin_val;
}

void aw9523b_pin_set_direction(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_state_t state) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    uint8_t reg = 0x04 + port;
    uint8_t reg_val = 0;
    esp_err_t err = aw9523b_readregs(dev, reg, &reg_val, 1);
    if (err < 0) {
        return;
    }
    if (state) {
        reg_val |= pin_mask;
    } else {
        reg_val &= ~pin_mask;
    }
    err = aw9523b_writeregs(dev, reg, &reg_val, 1);
}

aw9523b_pin_mode_t aw9523b_pin_get_mode(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    uint8_t reg = 0x12 + port;
    uint8_t reg_val = 0;
    esp_err_t err = aw9523b_readregs(dev, reg, &reg_val, 1);
    if (err < 0) {
        return AW9523B_PIN_MODE_INVALID;
    }
    aw9523b_pin_mode_t pin_mode = (reg_val & pin_mask)? AW9523B_PIN_MODE_GPIO : AW9523B_PIN_MODE_LED;
    return pin_mode;
}

void aw9523b_pin_set_mode(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_mode_t mode) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    uint8_t reg = 0x12 + port;
    uint8_t reg_val = 0;
    esp_err_t err = aw9523b_readregs(dev, reg, &reg_val, 1);
    if (err < 0) {
        return;
    }
    if (mode == AW9523B_PIN_MODE_GPIO) {
        reg_val |= pin_mask;
    } else {
        reg_val &= ~pin_mask;
    }
    err = aw9523b_writeregs(dev, reg, &reg_val, 1);
}

void aw9523b_irq_register(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_irq_callback_t callback, void* args) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_index = aw9523b_portpin(pin);

    dev->irq_handlers[port][pin_index] = (aw9523b_irq_handler_t) {
        .callback = callback,
        .args = args
    };
}

void aw9523b_irq_unregister(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    dev->irq_handlers[port][pin] = (aw9523b_irq_handler_t) {
        .callback = NULL,
        .args = NULL
    };
}

void aw9523b_irq_enable(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);
    uint8_t reg = 0x06 + port;
    dev->irq_enables[port] &= ~pin_mask;
    aw9523b_writeregs(dev, reg, &dev->irq_enables[port], 1);
}

void aw9523b_irq_disable(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);
    uint8_t reg = 0x06 + port;
    dev->irq_enables[port] |= pin_mask;
    aw9523b_writeregs(dev, reg, &dev->irq_enables[port], 1);
}

void aw9523b_irq_handler(aw9523b_device_t *dev) 
{
    uint8_t input_values[2];
    esp_err_t err = aw9523b_readregs(dev, 0x00, &input_values[0], 1);
    if ( err >= 0 )
    {
        err = aw9523b_readregs(dev, 0x01, &input_values[1], 1);
    }
    if ( err >= 0 )
    {
        for (uint8_t port = 0; port < 2; port++) 
        {
            uint8_t changed = input_values[port] ^ dev->last_input_values[port];
            dev->last_input_values[port] = input_values[port];
            for (uint8_t pin = 0; pin < 8; pin++) 
            {
                uint8_t pin_mask = 1 << pin;
                if ((~dev->irq_enables[port] & pin_mask & changed) 
                    && dev->irq_handlers[port][pin].callback ) 
                {
                    
                    uint8_t event = GPIO_INTR_NEGEDGE;
                    if ( input_values[port] & pin_mask )
                    {
                        event = GPIO_INTR_POSEDGE;
                    }
                    dev->irq_handlers[port][pin].callback(dev->irq_handlers[port][pin].args, event);
                }
            }
        }
    }
}

void aw9523b_pin_set_drive(aw9523b_device_t *dev, aw9523b_pin_t pin, uint8_t drive) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_index = aw9523b_portpin(pin);

    uint8_t drive_regs[2][8] = {
        {0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2a, 0x2b},
        {0x20, 0x21, 0x22, 0x23, 0x2c, 0x2d, 0x2e, 0x2f}
    };

    uint8_t reg = drive_regs[port][pin_index];
    aw9523b_writeregs(dev, reg, &drive, 1);
}