#ifndef _AW9523B_H_
#define _AW9523B_H_

#include "tildagon_i2c.h"
#include <stdint.h>

typedef uint8_t aw9523b_pin_t;
typedef enum{
  AW9523B_PIN_MODE_LED = 0,
  AW9523B_PIN_MODE_GPIO = 1,
  AW9523B_PIN_MODE_INVALID = -1

} aw9523b_pin_mode_t;
typedef bool aw9523b_pin_state_t;
typedef void (*aw9523b_irq_callback_t)(void*);

struct aw9523b_irq_handler{
  aw9523b_irq_callback_t callback;
  void* args;
};

typedef struct aw9523b_device{
  const tca9548a_i2c_mux_t *mux;
  tca9548a_i2c_port_t i2c_port;
  uint16_t i2c_addr;
  uint8_t last_input_values[2];
  uint8_t last_port_values[2];
  uint8_t direction[2];
  uint8_t irq_enables[2];
  uint8_t irq_got[2]; // 1 if input value is cached
  struct aw9523b_irq_handler irq_handlers[2][8];
} aw9523b_device_t;

void aw9523b_init(aw9523b_device_t *dev);

void aw9523b_irq_handler(aw9523b_device_t *dev);

void aw9523b_irq_register(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_irq_callback_t callback, void* args);
void aw9523b_irq_unregister(aw9523b_device_t *dev, aw9523b_pin_t pin);
void aw9523b_irq_enable(aw9523b_device_t *dev, aw9523b_pin_t pin);
void aw9523b_irq_disable(aw9523b_device_t *dev, aw9523b_pin_t pin);
void aw9523b_irq_configure(aw9523b_device_t *dev, aw9523b_pin_t pin, uint8_t mode);

bool aw9523b_pin_get_input(aw9523b_device_t *dev, aw9523b_pin_t pin);
bool aw9523b_pin_get_output(aw9523b_device_t *dev, aw9523b_pin_t pin);
void aw9523b_pin_set_output(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_state_t state);
bool aw9523b_pin_get_direction(aw9523b_device_t *dev, aw9523b_pin_t pin);
void aw9523b_pin_set_direction(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_state_t state);
aw9523b_pin_mode_t aw9523b_pin_get_mode(aw9523b_device_t *dev, aw9523b_pin_t pin);
void aw9523b_pin_set_mode(aw9523b_device_t *dev, aw9523b_pin_t pin, aw9523b_pin_mode_t mode);

void aw9523b_pin_set_drive(aw9523b_device_t *dev, aw9523b_pin_t pin, uint8_t drive);
uint8_t aw9523b_pin_get_drive(aw9523b_device_t *dev, aw9523b_pin_t pin);

#endif // _AW9523B_H_