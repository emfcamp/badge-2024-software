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

typedef struct {
    uint8_t cmd;
    const uint8_t *data;
    size_t data_len;
    uint16_t delay_ms;
} flow3r_bsp_lcd_cmd_t;

typedef struct {
    const uint8_t *header;
    size_t header_len;
    const flow3r_bsp_lcd_cmd_t *init_seq;
    size_t init_seq_len;
    const flow3r_bsp_lcd_cmd_t *prefix_seq;
    size_t prefix_seq_len;
    const flow3r_bsp_lcd_cmd_t *postfix_seq;
    size_t postfix_seq_len;
    bool is_allocated;
} flow3r_bsp_display_driver_t;

/**
 * @brief Free dynamically allocated fields of a display driver.
 */
void flow3r_bsp_display_driver_free(flow3r_bsp_display_driver_t *driver);

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
 * @brief Attach the display mirror sink.
 * 
 * @param port Hexpansion port (1..6)
 * @param sck Custom SCK GPIO (-1 for default)
 * @param mosi Custom MOSI GPIO (-1 for default)
 * @param cs Custom CS GPIO (-1 for default)
 * @param dc Custom DC GPIO (-1 for default)
 * @param baudrate Clock frequency in Hz
 * @param driver Driver descriptor (or NULL for raw data stream)
 * @return esp_err_t ESP_OK on success
 */
esp_err_t flow3r_bsp_display_mirror_attach(int port, int sck, int mosi, int cs, int dc, int baudrate, const flow3r_bsp_display_driver_t *driver);

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
 * @brief Execute an array of LCD commands with optional data and delays.
 */
void flow3r_bsp_display_exec_cmds(spi_device_handle_t spi, int cs_pin, int dc_pin, const flow3r_bsp_lcd_cmd_t *cmds, size_t count);
