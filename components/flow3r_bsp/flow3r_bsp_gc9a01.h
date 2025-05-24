#pragma once

#include <stdint.h>

#include "driver/ledc.h"
#include "driver/spi_master.h"

// Configuration structure for display.
//
// The display expects to be the only device on an SPI bus.
typedef struct {
    // Boolean: whether the display as a reset pin connected.
    uint8_t reset_used;
    // Boolean: whether the display as backlight control connected to the ESP
    // LED Control peripheral.
    uint8_t backlight_used;

    // Reset pin, if reset_used.
    uint8_t pin_rst;
    // SPI SCK pin.
    uint8_t pin_sck;
    // SPI MOSI pin.
    uint8_t pin_mosi;
    // SPI CS pin.
    uint8_t pin_cs;
    // Data/Command pin.
    uint8_t pin_dc;
    // Backlight control pin, if backlight_used.
    uint8_t pin_backlight;

    // Number of SPI host device (ie. bus) that the display will use.
    spi_host_device_t host;
} flow3r_bsp_gc9a01_config_t;

typedef struct {
    const flow3r_bsp_gc9a01_config_t *config;

    // Allocatged SPI device handle on configured bus.
    spi_device_handle_t spi;

    // Only if using backlight.
    ledc_channel_config_t bl_channel_config;
    ledc_timer_config_t bl_timer_config;

} flow3r_bsp_gc9a01_t;

// Initialize display structure based on config, and then actually initialize
// display hardware and ESP peripherals.
//
// The given gc9a01 structure does not need to be zeroed out.
//
// The given config structure must live as long as the display object lives. As
// currently displays cannot be de-initialized, this means that the
// configuration structure must live forever.
//
// An error will be returned if initialization failed. Initialization can be
// re-tried.
esp_err_t flow3r_bsp_gc9a01_init(flow3r_bsp_gc9a01_t *gc9a01,
                                 flow3r_bsp_gc9a01_config_t *config);

// Send a full-sized framebuffer to the display using interrupts/DMA, blocking
// FreeRTOS task until done.
//
// This must not be called if another blit is being performed. The user code
// should sequence access and make sure not more than one blit is performed
// simultaneously.
//
// if overlay is provided we want it composited in, the pixel format of overlay
// depends on bits - it is presumed to be the same size as fb.
esp_err_t flow3r_bsp_gc9a01_blit_full(flow3r_bsp_gc9a01_t *gc9a01, const void *fb, int i);

// Set backlight for display, using integer percent value (0-100, clamped).
esp_err_t flow3r_bsp_gc9a01_backlight_set(flow3r_bsp_gc9a01_t *gc9a01,
                                          uint8_t value);
