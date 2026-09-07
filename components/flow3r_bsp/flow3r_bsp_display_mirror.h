#pragma once

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "esp_err.h"
#include "driver/spi_master.h"

// ----------------------------------------------------------------------------
// High-Speed SPI Framebuffer Mirror Sink for Tildagon Hexpansions
// ----------------------------------------------------------------------------

typedef struct {
    int sck;
    int mosi;
    int cs;
    int dc;
} flow3r_bsp_port_pins_t;

/**
 * @brief Get high-speed SPI/LCD pin definitions for hexpansion port (1..6).
 */
const flow3r_bsp_port_pins_t *flow3r_bsp_display_get_port_pins(int port);

/**
 * @brief Acquire an SPI device on SPI2_HOST for a hexpansion port.
 */
esp_err_t flow3r_bsp_display_spi_acquire(int port, int baudrate, spi_device_handle_t *handle_out);

/**
 * @brief Acquire an SPI device on SPI2_HOST with explicit custom SCK and MOSI pins.
 */
esp_err_t flow3r_bsp_display_spi_acquire_pins(int port, int sck, int mosi, int baudrate, spi_device_handle_t *handle_out);

/**
 * @brief Release an SPI device previously acquired with flow3r_bsp_display_spi_acquire.
 */
void flow3r_bsp_display_spi_release(spi_device_handle_t handle);

/**
 * @brief Initialize and attach the SPI display mirror sink for a given hexpansion port.
 * 
 * @param port Hexpansion port number (1 to 6)
 * @param baudrate Clock frequency in Hz (e.g. 40000000 for PCB)
 * @param raw If true, sends raw RGB565 without "TDHD" header (for GC9A01 LCD hexpansion)
 * @return esp_err_t ESP_OK on success
 */
esp_err_t flow3r_bsp_display_mirror_init_port(int port, int baudrate, bool raw);

/**
 * @brief Initialize and attach the SPI display mirror sink with custom pin numbers.
 */
esp_err_t flow3r_bsp_display_mirror_init_custom(int port, int sck, int mosi, int cs, int dc, int baudrate, bool raw);

/**
 * @brief Initialize and attach the SPI display mirror sink with custom pin numbers.
 * 
 * @param sck_pin GPIO number for SCK
 * @param mosi_pin GPIO number for MOSI
 * @param cs_pin GPIO number for CS (Chip Select)
 * @param dc_pin GPIO number for DC (Data/Command select, or -1 if unused)
 * @param baudrate Clock frequency in Hz
 * @param raw If true, sends raw RGB565 without "TDHD" header
 * @return esp_err_t ESP_OK on success
 */
esp_err_t flow3r_bsp_display_mirror_init_pins(int sck_pin, int mosi_pin, int cs_pin, int dc_pin, int baudrate, bool raw);

/**
 * @brief Detach mirror sink for a specific port (or all if port <= 0).
 * 
 * @param port Hexpansion port number (1 to 6, or 0/negative for all)
 */
void flow3r_bsp_display_mirror_deinit_port(int port);

/**
 * @brief Detach all active mirror sinks.
 */
void flow3r_bsp_display_mirror_deinit_all(void);

/**
 * @brief Check if a mirror sink is active on a specific port.
 * 
 * @param port Hexpansion port number (1 to 6)
 * @return true if active, false otherwise
 */
bool flow3r_bsp_display_mirror_is_active(int port);

/**
 * @brief Send a 1-byte command to an SPI LCD panel with DC asserted LOW.
 */
void flow3r_bsp_display_lcd_send_cmd(spi_device_handle_t spi, int cs_pin, int dc_pin, uint8_t cmd);

/**
 * @brief Send a data buffer to an SPI LCD panel with DC asserted HIGH.
 */
void flow3r_bsp_display_lcd_send_data(spi_device_handle_t spi, int cs_pin, int dc_pin, const uint8_t *data, size_t len);

/**
 * @brief Initialize a GC9A01 LCD controller on the given SPI interface.
 */
void flow3r_bsp_display_lcd_init_gc9a01(spi_device_handle_t spi, int cs_pin, int dc_pin);
