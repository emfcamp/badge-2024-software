#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

// ----------------------------------------------------------------------------
// High-Speed SPI Framebuffer Mirror Sink for Tildagon Hexpansions
// ----------------------------------------------------------------------------

/**
 * @brief Initialize and attach the SPI display mirror sink for a given hexpansion port.
 * 
 * @param port Hexpansion port number (1 to 6)
 * @param baudrate Clock frequency in Hz (e.g. 4000000 for breadboard, 40000000 for PCB)
 * @return esp_err_t ESP_OK on success
 */
esp_err_t flow3r_bsp_display_mirror_init_port(int port, int baudrate);

/**
 * @brief Initialize and attach the SPI display mirror sink with custom pin numbers.
 * 
 * @param sck_pin GPIO number for SCK
 * @param mosi_pin GPIO number for MOSI
 * @param cs_pin GPIO number for CS (Chip Select)
 * @param baudrate Clock frequency in Hz
 * @return esp_err_t ESP_OK on success
 */
esp_err_t flow3r_bsp_display_mirror_init_pins(int sck_pin, int mosi_pin, int cs_pin, int baudrate);

/**
 * @brief Detach the mirror sink and release hardware SPI and DMA resources.
 */
void flow3r_bsp_display_mirror_deinit(void);

/**
 * @brief Check if the display mirror sink is currently active.
 * 
 * @return true if active, false otherwise
 */
bool flow3r_bsp_display_mirror_is_active(void);
