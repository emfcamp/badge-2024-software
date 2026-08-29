#include "flow3r_bsp_display_mirror.h"
#include "flow3r_bsp.h"

#include <string.h>
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "bsp-display-mirror";

#define MIRROR_SPI_HOST         SPI2_HOST
#define MAGIC_HEADER_LEN        4

// Port to HS GPIO mappings (SCK, MOSI, CS, MISO)
typedef struct {
    int sck;
    int mosi;
    int cs;
    int miso;
} port_hs_pins_t;

static const port_hs_pins_t PORT_PINS[7] = {
    { -1, -1, -1, -1 },         // 0: Invalid
    { 39, 40, 41, 42 },         // Port 1
    { 35, 36, 37, 38 },         // Port 2
    { 34, 33, 47, 48 },         // Port 3
    { 11, 14, 13, 12 },         // Port 4
    { 18, 16, 15, 17 },         // Port 5
    {  3,  4,  5,  6 },         // Port 6
};

static spi_device_handle_t mirror_spi = NULL;
static bool mirror_active = false;
static int mirror_cs_pin = -1;
static int mirror_sink_handle = -1;

// DMA-capable buffer for magic header
static uint8_t header_buf[4] WORD_ALIGNED_ATTR = { 'T', 'D', 'H', 'D' };

// ----------------------------------------------------------------------------
// Frame Sink Callback (Invoked on every display.end_frame)
// ----------------------------------------------------------------------------
static void mirror_sink_send_frame(const void *fb_data, size_t len, void *user_data) {
    if (!mirror_active || mirror_spi == NULL || fb_data == NULL || len == 0) {
        return;
    }

    // 1. Manually assert CS LOW if using manual CS, or let hardware SPI handle it
    if (mirror_cs_pin >= 0) {
        gpio_set_level(mirror_cs_pin, 0);
    }

    // 2. Transmit 4-byte magic header "TDHD"
    spi_transaction_t tx_hdr;
    memset(&tx_hdr, 0, sizeof(tx_hdr));
    tx_hdr.length = MAGIC_HEADER_LEN * 8;
    tx_hdr.tx_buffer = header_buf;
    spi_device_polling_transmit(mirror_spi, &tx_hdr);

    // 3. Transmit pixel payload (115,200 bytes) via SPI DMA
    spi_transaction_t tx_data;
    memset(&tx_data, 0, sizeof(tx_data));
    tx_data.length = len * 8;
    tx_data.tx_buffer = fb_data;
    spi_device_polling_transmit(mirror_spi, &tx_data);

    // 4. Deassert CS HIGH
    if (mirror_cs_pin >= 0) {
        gpio_set_level(mirror_cs_pin, 1);
    }
}

// ----------------------------------------------------------------------------
// Public API
// ----------------------------------------------------------------------------

esp_err_t flow3r_bsp_display_mirror_init_pins(int sck_pin, int mosi_pin, int cs_pin, int baudrate) {
    flow3r_bsp_display_mirror_deinit();

    if (baudrate <= 0) {
        baudrate = 40000000; // Default 40 MHz
    }

    ESP_LOGI(TAG, "Initializing SPI display mirror on SCK=%d, MOSI=%d, CS=%d @ %d Hz",
             sck_pin, mosi_pin, cs_pin, baudrate);

    // Configure manual CS pin for precise transaction framing
    mirror_cs_pin = cs_pin;
    gpio_config_t cs_cfg = {
        .pin_bit_mask = (1ULL << cs_pin),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&cs_cfg);
    gpio_set_level(cs_pin, 1); // Idle HIGH

    // Configure SPI bus
    spi_bus_config_t buscfg = {
        .miso_io_num = -1,
        .mosi_io_num = mosi_pin,
        .sclk_io_num = sck_pin,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 115200 + 128,
        .flags = SPICOMMON_BUSFLAG_MASTER,
    };

    esp_err_t ret = spi_bus_initialize(MIRROR_SPI_HOST, &buscfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "spi_bus_initialize failed: %s", esp_err_to_name(ret));
        return ret;
    }

    // Configure SPI device
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = baudrate,
        .mode = 0,                  // SPI Mode 0 (CPOL=0, CPHA=0)
        .spics_io_num = -1,         // Handled manually via mirror_cs_pin
        .queue_size = 2,
        .flags = SPI_DEVICE_NO_DUMMY,
    };

    ret = spi_bus_add_device(MIRROR_SPI_HOST, &devcfg, &mirror_spi);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "spi_bus_add_device failed: %s", esp_err_to_name(ret));
        spi_bus_free(MIRROR_SPI_HOST);
        return ret;
    }

    // Register with generic display subsystem
    flow3r_bsp_display_sink_t sink = {
        .send_frame = mirror_sink_send_frame,
        .user_data = NULL,
    };
    mirror_sink_handle = flow3r_bsp_display_register_sink(&sink);

    mirror_active = true;
    ESP_LOGI(TAG, "Display mirror sink successfully attached (handle: %d).", mirror_sink_handle);
    return ESP_OK;
}

esp_err_t flow3r_bsp_display_mirror_init_port(int port, int baudrate) {
    if (port < 1 || port > 6) {
        ESP_LOGE(TAG, "Invalid hexpansion port %d (must be 1..6)", port);
        return ESP_ERR_INVALID_ARG;
    }
    const port_hs_pins_t *p = &PORT_PINS[port];
    return flow3r_bsp_display_mirror_init_pins(p->sck, p->mosi, p->cs, baudrate);
}

void flow3r_bsp_display_mirror_deinit(void) {
    if (!mirror_active && mirror_spi == NULL) {
        return;
    }

    // Deregister from display pipeline
    if (mirror_sink_handle > 0) {
        flow3r_bsp_display_unregister_sink(mirror_sink_handle);
        mirror_sink_handle = -1;
    }
    mirror_active = false;

    if (mirror_spi != NULL) {
        spi_bus_remove_device(mirror_spi);
        mirror_spi = NULL;
    }

    spi_bus_free(MIRROR_SPI_HOST);
    if (mirror_cs_pin >= 0) {
        gpio_reset_pin(mirror_cs_pin);
        mirror_cs_pin = -1;
    }

    ESP_LOGI(TAG, "Display mirror sink detached.");
}

bool flow3r_bsp_display_mirror_is_active(void) {
    return mirror_active;
}
