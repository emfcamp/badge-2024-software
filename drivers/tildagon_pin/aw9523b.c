#include "aw9523b.h"
#include <assert.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "tildagon_i2c.h"
#include "tildagon_i2c_manager.h"
#include "esp_err.h"
//#include "esp_log.h"

#define READ ( MP_MACHINE_I2C_FLAG_WRITE1 | MP_MACHINE_I2C_FLAG_READ | MP_MACHINE_I2C_FLAG_STOP )
#define WRITE MP_MACHINE_I2C_FLAG_STOP

//static const char *TAG = "aw9523b";

static int8_t m_aw9523b_i2c_manager_job_handle = -1;
static SemaphoreHandle_t m_aw9523b_i2c_manager_job_sem = NULL;

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
    mp_machine_i2c_buf_t buffer[2] = { { .len = 1, .buf = &reg },
                                       { .len = nregs, .buf = regs } };
    return tildagon_mux_i2c_transaction(dev->mux, dev->i2c_addr, 2, (mp_machine_i2c_buf_t*)&buffer, READ);
}

static esp_err_t aw9523b_writeregs(aw9523b_device_t *dev, uint8_t reg, const uint8_t *regs, size_t nregs) {
    uint8_t buf[nregs+1];
    buf[0] = reg;
    memcpy(buf+1, regs, nregs);
    mp_machine_i2c_buf_t buffer[1] = { { .len = nregs+1, .buf = buf } };
    return tildagon_mux_i2c_transaction(dev->mux, dev->i2c_addr, 1, (mp_machine_i2c_buf_t*)&buffer, WRITE);
}


/* Structure for a single register write via the I2C manager.
   This is used to store the details of a pending write operation
   so that the I2C manager can execute it asynchronously. */
typedef struct {
    uint8_t reg;
    uint8_t value;
    uint8_t i2c_addr : 7;
    uint8_t mux_port : 3;
} aw9523b_single_reg_write_t;

static aw9523b_single_reg_write_t m_aw9523b_single_reg_write;

static esp_err_t aw9523b_writeregs_via_i2c_manager(aw9523b_device_t *dev, uint8_t reg, const uint8_t *regs, size_t nregs) {
    if ((nregs > 1) || (m_aw9523b_i2c_manager_job_sem == NULL) || (m_aw9523b_i2c_manager_job_handle < 0)) {
        return aw9523b_writeregs(dev, reg, regs, nregs);
    }
    if (xSemaphoreTake(m_aw9523b_i2c_manager_job_sem, pdMS_TO_TICKS(100)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }
    m_aw9523b_single_reg_write.reg = reg;
    m_aw9523b_single_reg_write.value = regs[0];
    m_aw9523b_single_reg_write.i2c_addr = (uint8_t)dev->i2c_addr;
    m_aw9523b_single_reg_write.mux_port = (uint8_t)dev->mux->port;

    //ESP_LOGI(TAG, "Arm: reg=0x%02X, value=0x%02X", m_aw9523b_single_reg_write.reg, m_aw9523b_single_reg_write.value);
    if (!tildagon_i2c_mgr_run_once(m_aw9523b_i2c_manager_job_handle)) {
        //ESP_LOGW(TAG, "Failed to arm run once job - giving semaphore");
        xSemaphoreGive(m_aw9523b_i2c_manager_job_sem);
        return aw9523b_writeregs(dev, reg, regs, nregs);
    }
    return ESP_OK;
}


// callback for the i2c manager to write single registers e.g. to set pin states
// Two phases:
// - run - to do the actual I2C write,
// - complete - to release the semaphore only AFTER the i2c_manager has finished the transaction
// otherwise we can try to start another i2c_manager job while the previous one is still running
void aw9523b_writereg_handler(tildagon_i2c_mgr_phase_t phase)
{
    if ((phase == TILDAGON_I2C_MGR_PHASE_COMPLETE) && (m_aw9523b_i2c_manager_job_sem)) {
        xSemaphoreGive(m_aw9523b_i2c_manager_job_sem);
        return;
    }

    // TILDAGON_I2C_MGR_PHASE_RUN
    //ESP_LOGI(TAG, "Write reg=0x%02X, value=0x%02X", m_aw9523b_single_reg_write.reg, m_aw9523b_single_reg_write.value);
    uint8_t buffer_data[2] = { m_aw9523b_single_reg_write.reg, m_aw9523b_single_reg_write.value };
    mp_machine_i2c_buf_t buffer[1] = { { .len = sizeof(buffer_data), .buf = buffer_data } };
    tildagon_mux_i2c_obj_t *mux = tildagon_get_mux_obj(m_aw9523b_single_reg_write.mux_port);

    tildagon_mux_i2c_transaction(mux, m_aw9523b_single_reg_write.i2c_addr, 1,
                                (mp_machine_i2c_buf_t *)&buffer, WRITE );
}


/* The default output values of the AW9523B depend on its I2C address */
const uint8_t aw9523b_default_output_values[4][2] = {{ 0x00U, 0x00U }, { 0x0FU, 0x0FU }, { 0xF0U, 0xF0U }, { 0xFFU, 0xFFU }};

void aw9523b_init(aw9523b_device_t *dev)
{
    aw9523b_writeregs(dev, 0x7F, (const uint8_t*)"\x00", 2);        // Soft Reset
    aw9523b_writeregs(dev, 0x06, (const uint8_t*)"\xff\xff", 2);    // Disable interrupts on all pins
    aw9523b_writeregs(dev, 0x04, (const uint8_t*)"\xff\xff", 2);    // Set all pins as inputs
    aw9523b_writeregs(dev, 0x11, (const uint8_t*)"\x10", 1);        // Set P0 port to push-pull output
    // 0x00 is the default setting for the PWM registers anyway, so no need to explicitly write it
    //aw9523b_writeregs(dev, 0x20, (const uint8_t*)"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 16);

    dev->irq_enables[0] = 0xFFU;
    dev->irq_enables[1] = 0xFFU;
    aw9523b_pin_get_input(dev, 0);  // initialise last_input_values for port 0
    aw9523b_pin_get_input(dev, 8);  // initialise last_input_values for port 1

    // direction was just written above; seed the shadow directly rather than reading it back
    dev->direction_values[0] = 0xFFU;
    dev->direction_values[1] = 0xFFU;

    // outputs were left at their power-on-reset value, so seed the shadow directly rather than reading it back
    dev->output_values[0] = aw9523b_default_output_values[(dev->i2c_addr & 0x03)][0];
    dev->output_values[1] = aw9523b_default_output_values[(dev->i2c_addr & 0x03)][1];

    // mode was left at its power-on-reset value, so seed the shadow directly
    dev->mode_values[0] = 0xFFU;
    dev->mode_values[1] = 0xFFU;

    // register a callback job with the i2c manager for use in writing single registers
    if (m_aw9523b_i2c_manager_job_handle < 0) {
        m_aw9523b_i2c_manager_job_handle = (int8_t)tildagon_i2c_mgr_register_phased(
            aw9523b_writereg_handler, TILDAGON_I2C_MGR_PERIOD_OFF, true );
    }
    if (m_aw9523b_i2c_manager_job_sem == NULL) {
        m_aw9523b_i2c_manager_job_sem = xSemaphoreCreateBinary();
        if (m_aw9523b_i2c_manager_job_sem) {
            //ESP_LOGI(TAG, "Creating and giving semaphore");
            xSemaphoreGive(m_aw9523b_i2c_manager_job_sem);
        }
    }
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

    return (dev->output_values[port] & pin_mask) != 0;
}

void aw9523b_pin_set_output(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_state_t state) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);
    uint8_t reg = 0x02 + port;

    if (state) {
        dev->output_values[port] |= pin_mask;
    } else {
        dev->output_values[port] &= ~pin_mask;
    }
    aw9523b_writeregs_via_i2c_manager(dev, reg, &dev->output_values[port], 1);
}

void aw9523b_pin_toggle(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);
    uint8_t reg = 0x02 + port;

    if (dev->output_values[port] & pin_mask) {
        dev->output_values[port] &= ~pin_mask;
    } else {
        dev->output_values[port] |= pin_mask;
    }
    aw9523b_writeregs_via_i2c_manager(dev, reg, &dev->output_values[port], 1);
}

bool aw9523b_pin_get_direction(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    return (dev->direction_values[port] & pin_mask) != 0;
}

void aw9523b_pin_set_direction(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_state_t state) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);
    uint8_t reg = 0x04 + port;

    if (state) {
        dev->direction_values[port] |= pin_mask;
    } else {
        dev->direction_values[port] &= ~pin_mask;
    }
    aw9523b_writeregs_via_i2c_manager(dev, reg, &dev->direction_values[port], 1);
}

aw9523b_pin_mode_t aw9523b_pin_get_mode(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);

    return (dev->mode_values[port] & pin_mask) ? AW9523B_PIN_MODE_GPIO : AW9523B_PIN_MODE_LED;
}

void aw9523b_pin_set_mode(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_mode_t mode) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);
    uint8_t reg = 0x12 + port;

    if (mode == AW9523B_PIN_MODE_GPIO) {
        dev->mode_values[port] |= pin_mask;
    } else {
        dev->mode_values[port] &= ~pin_mask;
    }
    aw9523b_writeregs_via_i2c_manager(dev, reg, &dev->mode_values[port], 1);
}

void aw9523b_irq_register(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_irq_callback_t callback) {
    aw9523b_check_valid_pin(pin);
    dev->irq_handlers[aw9523b_portnum(pin)][aw9523b_portpin(pin)] = callback;
}

void aw9523b_irq_unregister(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    dev->irq_handlers[aw9523b_portnum(pin)][aw9523b_portpin(pin)] = NULL;
}

void aw9523b_irq_enable(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);
    uint8_t reg = 0x06 + port;
    dev->irq_enables[port] &= ~pin_mask;
    aw9523b_writeregs_via_i2c_manager(dev, reg, &dev->irq_enables[port], 1);
}

void aw9523b_irq_disable(aw9523b_device_t *dev, aw9523b_pin_t pin) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_mask = 1 << aw9523b_portpin(pin);
    uint8_t reg = 0x06 + port;
    dev->irq_enables[port] |= pin_mask;
    aw9523b_writeregs_via_i2c_manager(dev, reg, &dev->irq_enables[port], 1);
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
                    && dev->irq_handlers[port][pin] )
                {

                    uint8_t event = GPIO_INTR_NEGEDGE;
                    if ( input_values[port] & pin_mask )
                    {
                        event = GPIO_INTR_POSEDGE;
                    }
                    dev->irq_handlers[port][pin]( dev, (aw9523b_pin_t)((port * 8) + pin), event );
                }
            }
        }
    }
}

void aw9523b_pin_set_drive(aw9523b_device_t *dev, aw9523b_pin_t pin, uint8_t drive) {
    aw9523b_check_valid_pin(pin);
    uint8_t port = aw9523b_portnum(pin);
    uint8_t pin_index = aw9523b_portpin(pin);

    // static const so this table lives once in flash rather than being rebuilt on the stack per call
    static const uint8_t drive_regs[2][8] = {
        {0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2a, 0x2b},
        {0x20, 0x21, 0x22, 0x23, 0x2c, 0x2d, 0x2e, 0x2f}
    };

    uint8_t reg = drive_regs[port][pin_index];
    aw9523b_writeregs_via_i2c_manager(dev, reg, &drive, 1);
}
