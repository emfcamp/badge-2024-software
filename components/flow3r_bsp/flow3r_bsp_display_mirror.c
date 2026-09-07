#include "flow3r_bsp_display_mirror.h"
#include "flow3r_bsp.h"

#include <string.h>
#include <stdlib.h>
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "bsp-display-mirror";

#define MIRROR_SPI_HOST         SPI2_HOST
#define MAGIC_HEADER_LEN        4

static const flow3r_bsp_port_pins_t PORT_PINS[7] = {
    { -1, -1, -1, -1 },         // 0: Invalid
    { 39, 40, 41, 42 },         // Port 1: SCK=HS0(39), MOSI=HS1(40), CS=HS2(41), DC=HS3(42)
    { 35, 36, 37, 38 },         // Port 2: SCK=HS0(35), MOSI=HS1(36), CS=HS2(37), DC=HS3(38)
    { 34, 33, 47, 48 },         // Port 3: SCK=HS0(34), MOSI=HS1(33), CS=HS2(47), DC=HS3(48)
    { 11, 14, 13, 12 },         // Port 4: SCK=HS0(11), MOSI=HS1(14), CS=HS2(13), DC=HS3(12)
    { 18, 16, 15, 17 },         // Port 5: SCK=HS0(18), MOSI=HS1(16), CS=HS2(15), DC=HS3(17)
    {  3,  4,  5,  6 },         // Port 6: SCK=HS0(3),  MOSI=HS1(4),  CS=HS2(5),  DC=HS3(6)
};

const flow3r_bsp_port_pins_t *flow3r_bsp_display_get_port_pins(int port) {
    if (port < 1 || port > 6) return NULL;
    return &PORT_PINS[port];
}

typedef struct {
    bool active;
    int port;
    int cs_pin;
    int dc_pin;
    int sink_handle;
    bool raw;
    spi_device_handle_t spi;
} mirror_port_state_t;

static mirror_port_state_t mirror_ports[7];
static bool spi2_bus_inited = false;
static int spi2_active_port = -1;
static int spi2_active_sck = -1;
static int spi2_active_mosi = -1;
static int spi2_user_count = 0;

// DMA-capable buffer for magic header
static uint8_t header_buf[4] WORD_ALIGNED_ATTR = { 'T', 'D', 'H', 'D' };

// ----------------------------------------------------------------------------
// Low-Level LCD Panel Commands (GC9A01 / Raw Displays)
// ----------------------------------------------------------------------------

void flow3r_bsp_display_lcd_send_cmd(spi_device_handle_t spi, int cs_pin, int dc_pin, uint8_t cmd) {
    if (spi == NULL) return;
    if (dc_pin >= 0) gpio_set_level(dc_pin, 0); // Command mode
    if (cs_pin >= 0) gpio_set_level(cs_pin, 0);

    spi_transaction_t t;
    memset(&t, 0, sizeof(t));
    t.flags = SPI_TRANS_USE_TXDATA;
    t.length = 8;
    t.tx_data[0] = cmd;
    spi_device_polling_transmit(spi, &t);

    if (cs_pin >= 0) gpio_set_level(cs_pin, 1);
}

void flow3r_bsp_display_lcd_send_data(spi_device_handle_t spi, int cs_pin, int dc_pin, const uint8_t *data, size_t len) {
    if (spi == NULL || data == NULL || len == 0) return;
    if (dc_pin >= 0) gpio_set_level(dc_pin, 1); // Data mode
    if (cs_pin >= 0) gpio_set_level(cs_pin, 0);

    size_t offset = 0;
    while (offset < len) {
        size_t chunk = len - offset;
        if (chunk > 4) chunk = 4;

        spi_transaction_t t;
        memset(&t, 0, sizeof(t));
        t.flags = SPI_TRANS_USE_TXDATA;
        t.length = chunk * 8;
        memcpy(t.tx_data, data + offset, chunk);
        spi_device_polling_transmit(spi, &t);

        offset += chunk;
    }

    if (cs_pin >= 0) gpio_set_level(cs_pin, 1);
}

void flow3r_bsp_display_lcd_init_gc9a01(spi_device_handle_t spi, int cs_pin, int dc_pin) {
    ESP_LOGI(TAG, "Initializing GC9A01 LCD controller (CS=%d, DC=%d)...", cs_pin, dc_pin);

    static const uint8_t c_eb[] = { 0x14 };
    static const uint8_t c_84[] = { 0x40 };
    static const uint8_t c_ff_1[] = { 0xff };
    static const uint8_t c_88[] = { 0x0a };
    static const uint8_t c_89[] = { 0x21 };
    static const uint8_t c_8a[] = { 0x00 };
    static const uint8_t c_8b[] = { 0x80 };
    static const uint8_t c_01[] = { 0x01 };
    static const uint8_t c_b6[] = { 0x00, 0x20 };
    static const uint8_t c_90[] = { 0x08, 0x08, 0x08, 0x08 };
    static const uint8_t c_bd[] = { 0x06 };
    static const uint8_t c_bc[] = { 0x00 };
    static const uint8_t c_ff_3[] = { 0x60, 0x01, 0x04 };
    static const uint8_t c_c3[] = { 0x13 };
    static const uint8_t c_c4[] = { 0x13 };
    static const uint8_t c_c9[] = { 0x22 };
    static const uint8_t c_be[] = { 0x11 };
    static const uint8_t c_e1[] = { 0x10, 0x0e };
    static const uint8_t c_df[] = { 0x21, 0x0c, 0x02 };
    static const uint8_t c_f0[] = { 0x45, 0x09, 0x08, 0x08, 0x26, 0x2a };
    static const uint8_t c_f1[] = { 0x43, 0x70, 0x72, 0x36, 0x37, 0x6f };
    static const uint8_t c_ed[] = { 0x1b, 0x0b };
    static const uint8_t c_ae[] = { 0x77 };
    static const uint8_t c_cd[] = { 0x63 };
    static const uint8_t c_70[] = { 0x07, 0x07, 0x04, 0x0e, 0x0f, 0x09, 0x07, 0x08, 0x03 };
    static const uint8_t c_e8[] = { 0x34 };
    static const uint8_t c_62[] = { 0x18, 0x0d, 0x71, 0xed, 0x70, 0x70, 0x18, 0x0f, 0x71, 0xef, 0x70, 0x70 };
    static const uint8_t c_63[] = { 0x18, 0x11, 0x71, 0xf1, 0x70, 0x70, 0x18, 0x13, 0x71, 0xf3, 0x70, 0x70 };
    static const uint8_t c_64[] = { 0x28, 0x29, 0xf1, 0x01, 0xf1, 0x00, 0x07 };
    static const uint8_t c_66[] = { 0x3c, 0x00, 0xcd, 0x67, 0x45, 0x45, 0x10, 0x00, 0x00, 0x00 };
    static const uint8_t c_67[] = { 0x00, 0x3c, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98 };
    static const uint8_t c_74[] = { 0x10, 0x85, 0x80, 0x00, 0x00, 0x4e, 0x00 };
    static const uint8_t c_98[] = { 0x3e, 0x07 };
    static const uint8_t c_madctl[] = { 0xc8 }; // BGR + MX + MY (matches native rotation)
    static const uint8_t c_colmod[] = { 0x05 }; // 16-bit RGB565
    static const uint8_t c_window[] = { 0x00, 0x00, 0x00, 0xef }; // 0..239

    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xef);
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xeb); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_eb, sizeof(c_eb));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xfe);
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xef);
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xeb); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_eb, sizeof(c_eb));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x84); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_84, sizeof(c_84));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x85); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_ff_1, sizeof(c_ff_1));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x86); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_ff_1, sizeof(c_ff_1));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x87); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_ff_1, sizeof(c_ff_1));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x88); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_88, sizeof(c_88));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x89); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_89, sizeof(c_89));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x8a); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_8a, sizeof(c_8a));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x8b); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_8b, sizeof(c_8b));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x8c); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_01, sizeof(c_01));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x8d); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_01, sizeof(c_01));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x8e); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_ff_1, sizeof(c_ff_1));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x8f); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_ff_1, sizeof(c_ff_1));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xb6); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_b6, sizeof(c_b6));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x90); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_90, sizeof(c_90));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xbd); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_bd, sizeof(c_bd));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xbc); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_bc, sizeof(c_bc));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xff); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_ff_3, sizeof(c_ff_3));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xc3); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_c3, sizeof(c_c3));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xc4); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_c4, sizeof(c_c4));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xc9); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_c9, sizeof(c_c9));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xbe); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_be, sizeof(c_be));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xe1); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_e1, sizeof(c_e1));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xdf); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_df, sizeof(c_df));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xf0); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_f0, sizeof(c_f0));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xf1); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_f1, sizeof(c_f1));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xf2); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_f0, sizeof(c_f0));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xf3); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_f1, sizeof(c_f1));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xed); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_ed, sizeof(c_ed));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xae); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_ae, sizeof(c_ae));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xcd); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_cd, sizeof(c_cd));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x70); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_70, sizeof(c_70));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0xe8); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_e8, sizeof(c_e8));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x62); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_62, sizeof(c_62));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x63); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_63, sizeof(c_63));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x64); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_64, sizeof(c_64));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x66); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_66, sizeof(c_66));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x67); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_67, sizeof(c_67));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x74); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_74, sizeof(c_74));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x98); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_98, sizeof(c_98));

    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x35); // TEON
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x21); // INVON
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x11); // SLPOUT
    vTaskDelay(pdMS_TO_TICKS(120));

    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x36); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_madctl, sizeof(c_madctl));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x3a); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_colmod, sizeof(c_colmod));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x29); // DISPON
    vTaskDelay(pdMS_TO_TICKS(20));

    // Set 240x240 address window and enter RAMWR
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x2a); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_window, sizeof(c_window));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x2b); flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, c_window, sizeof(c_window));
    flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, 0x2c); // RAMWR

    if (dc_pin >= 0) {
        gpio_set_level(dc_pin, 1); // Set to data mode for streaming
    }
}

// ----------------------------------------------------------------------------
// Frame Sink Callback (Invoked on every display.end_frame)
// ----------------------------------------------------------------------------

static void mirror_sink_send_frame(const void *fb_data, size_t len, void *user_data) {
    mirror_port_state_t *mp = (mirror_port_state_t *)user_data;
    if (mp == NULL || !mp->active || mp->spi == NULL || fb_data == NULL || len == 0) {
        return;
    }

    // 1. Manually assert CS LOW
    if (mp->cs_pin >= 0) {
        gpio_set_level(mp->cs_pin, 0);
    }

    // 2. If driving raw LCD (GC9A01), send RAMWR command (0x2C) with DC=0 while holding CS LOW
    if (mp->raw && mp->dc_pin >= 0) {
        gpio_set_level(mp->dc_pin, 0); // Command mode
        spi_transaction_t cmd_tx;
        memset(&cmd_tx, 0, sizeof(cmd_tx));
        cmd_tx.flags = SPI_TRANS_USE_TXDATA;
        cmd_tx.length = 8;
        cmd_tx.tx_data[0] = 0x2c;
        spi_device_polling_transmit(mp->spi, &cmd_tx);

        gpio_set_level(mp->dc_pin, 1); // Switch to Data mode (CS remains LOW!)
    }

    // 3. Transmit 4-byte magic header "TDHD" unless in raw mode
    if (!mp->raw) {
        spi_transaction_t tx_hdr;
        memset(&tx_hdr, 0, sizeof(tx_hdr));
        tx_hdr.flags = SPI_TRANS_USE_TXDATA;
        tx_hdr.length = 4 * 8;
        tx_hdr.tx_data[0] = 'T';
        tx_hdr.tx_data[1] = 'D';
        tx_hdr.tx_data[2] = 'H';
        tx_hdr.tx_data[3] = 'D';
        spi_device_polling_transmit(mp->spi, &tx_hdr);
    }

    // 4. Transmit pixel payload via SPI DMA in chunks while holding CS LOW
    const uint8_t *src = (const uint8_t *)fb_data;
    size_t remaining = len;
    while (remaining > 0) {
        size_t chunk = (remaining > 4096) ? 4096 : remaining;
        spi_transaction_t tx_data;
        memset(&tx_data, 0, sizeof(tx_data));
        tx_data.length = chunk * 8;
        tx_data.tx_buffer = src;
        spi_device_polling_transmit(mp->spi, &tx_data);
        src += chunk;
        remaining -= chunk;
    }

    // 5. Deassert CS HIGH only after entire frame transfer is complete
    if (mp->cs_pin >= 0) {
        gpio_set_level(mp->cs_pin, 1);
    }
}

// ----------------------------------------------------------------------------
// Public API
// ----------------------------------------------------------------------------

esp_err_t flow3r_bsp_display_mirror_init_pins(int sck_pin, int mosi_pin, int cs_pin, int dc_pin, int baudrate, bool raw) {
    if (baudrate <= 0) {
        baudrate = 40000000;
    }

    ESP_LOGI(TAG, "Configuring SPI mirror on SCK=%d, MOSI=%d, CS=%d, DC=%d @ %d Hz (raw=%d)",
             sck_pin, mosi_pin, cs_pin, dc_pin, baudrate, (int)raw);

    // Configure CS pin (idle HIGH)
    if (cs_pin >= 0) {
        gpio_config_t cs_cfg = {
            .pin_bit_mask = (1ULL << cs_pin),
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&cs_cfg);
        gpio_set_level(cs_pin, 1);
    }

    // Configure DC pin (idle HIGH)
    if (dc_pin >= 0) {
        gpio_config_t dc_cfg = {
            .pin_bit_mask = (1ULL << dc_pin),
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&dc_cfg);
        gpio_set_level(dc_pin, 1);
    }

    return ESP_OK;
}

esp_err_t flow3r_bsp_display_spi_acquire_pins(int port, int sck, int mosi, int baudrate, spi_device_handle_t *handle_out) {
    if (handle_out == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (baudrate <= 0) {
        baudrate = 40000000;
    }

    if (sck < 0 || mosi < 0) {
        if (port < 1 || port > 6) {
            return ESP_ERR_INVALID_ARG;
        }
        const flow3r_bsp_port_pins_t *p = &PORT_PINS[port];
        if (sck < 0) sck = p->sck;
        if (mosi < 0) mosi = p->mosi;
    }

    // If SPI2 is active with different pins, clean it up
    if (spi2_bus_inited && (spi2_active_sck != sck || spi2_active_mosi != mosi)) {
        ESP_LOGW(TAG, "Reallocating SPI2_HOST with new pins (SCK: %d->%d, MOSI: %d->%d)",
                 spi2_active_sck, sck, spi2_active_mosi, mosi);
        spi_bus_free(MIRROR_SPI_HOST);
        spi2_bus_inited = false;
        spi2_user_count = 0;
    }

    if (!spi2_bus_inited) {
        spi_bus_config_t buscfg = {
            .miso_io_num = -1,
            .mosi_io_num = mosi,
            .sclk_io_num = sck,
            .quadwp_io_num = -1,
            .quadhd_io_num = -1,
            .max_transfer_sz = 115200 + 128,
            .flags = SPICOMMON_BUSFLAG_MASTER,
        };

        esp_err_t ret = spi_bus_initialize(MIRROR_SPI_HOST, &buscfg, SPI_DMA_CH_AUTO);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "spi_bus_initialize failed (SCK=%d, MOSI=%d): %s", sck, mosi, esp_err_to_name(ret));
            return ret;
        }
        spi2_bus_inited = true;
        spi2_active_port = port;
        spi2_active_sck = sck;
        spi2_active_mosi = mosi;
        spi2_user_count = 0;
    }

    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = baudrate,
        .mode = 0,
        .spics_io_num = -1,
        .queue_size = 2,
        .flags = SPI_DEVICE_NO_DUMMY,
    };

    esp_err_t ret = spi_bus_add_device(MIRROR_SPI_HOST, &devcfg, handle_out);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "spi_bus_add_device failed: %s", esp_err_to_name(ret));
        return ret;
    }

    spi2_user_count++;
    return ESP_OK;
}

esp_err_t flow3r_bsp_display_spi_acquire(int port, int baudrate, spi_device_handle_t *handle_out) {
    return flow3r_bsp_display_spi_acquire_pins(port, -1, -1, baudrate, handle_out);
}

void flow3r_bsp_display_spi_release(spi_device_handle_t handle) {
    if (handle == NULL) return;
    spi_bus_remove_device(handle);
    if (spi2_user_count > 0) {
        spi2_user_count--;
    }
    if (spi2_user_count == 0 && spi2_bus_inited) {
        spi_bus_free(MIRROR_SPI_HOST);
        spi2_bus_inited = false;
        spi2_active_port = -1;
        spi2_active_sck = -1;
        spi2_active_mosi = -1;
    }
}

esp_err_t flow3r_bsp_display_mirror_init_custom(int port, int sck, int mosi, int cs, int dc, int baudrate, bool raw) {
    flow3r_bsp_display_init();
    if (port < 1 || port > 6) {
        ESP_LOGE(TAG, "Invalid hexpansion port %d (must be 1..6)", port);
        return ESP_ERR_INVALID_ARG;
    }

    const flow3r_bsp_port_pins_t *p = &PORT_PINS[port];
    if (sck < 0) sck = p->sck;
    if (mosi < 0) mosi = p->mosi;
    if (cs < 0) cs = p->cs;
    if (dc < 0) dc = p->dc;

    mirror_port_state_t *mp = &mirror_ports[port];
    if (mp->active) {
        flow3r_bsp_display_mirror_deinit_port(port);
    }

    esp_err_t ret = flow3r_bsp_display_mirror_init_pins(sck, mosi, cs, dc, baudrate, raw);
    if (ret != ESP_OK) {
        return ret;
    }

    ret = flow3r_bsp_display_spi_acquire_pins(port, sck, mosi, baudrate, &mp->spi);
    if (ret != ESP_OK) {
        return ret;
    }

    mp->port = port;
    mp->cs_pin = cs;
    mp->dc_pin = dc;
    mp->raw = raw;
    mp->active = true;

    // If driving a raw GC9A01 display, wake it up and initialize window
    if (raw) {
        flow3r_bsp_display_lcd_init_gc9a01(mp->spi, mp->cs_pin, mp->dc_pin);
    }

    // Register with generic dynamic display sink subsystem
    flow3r_bsp_display_sink_t sink = {
        .send_frame = mirror_sink_send_frame,
        .user_data = mp,
    };
    mp->sink_handle = flow3r_bsp_display_register_sink(&sink);

    ESP_LOGI(TAG, "Display mirror attached on port %d [SCK=%d, MOSI=%d, CS=%d, DC=%d] (sink handle: %d, raw: %d).",
             port, sck, mosi, cs, dc, mp->sink_handle, (int)raw);
    return ESP_OK;
}

esp_err_t flow3r_bsp_display_mirror_init_port(int port, int baudrate, bool raw) {
    return flow3r_bsp_display_mirror_init_custom(port, -1, -1, -1, -1, baudrate, raw);
}

void flow3r_bsp_display_mirror_deinit_port(int port) {
    if (port < 1 || port > 6) {
        return;
    }

    mirror_port_state_t *mp = &mirror_ports[port];
    if (!mp->active) {
        return;
    }

    if (mp->sink_handle > 0) {
        flow3r_bsp_display_unregister_sink(mp->sink_handle);
        mp->sink_handle = -1;
    }

    if (mp->spi != NULL) {
        flow3r_bsp_display_spi_release(mp->spi);
        mp->spi = NULL;
    }

    if (mp->cs_pin >= 0) {
        gpio_reset_pin(mp->cs_pin);
        mp->cs_pin = -1;
    }
    if (mp->dc_pin >= 0) {
        gpio_reset_pin(mp->dc_pin);
        mp->dc_pin = -1;
    }

    mp->active = false;
    ESP_LOGI(TAG, "Display mirror detached from port %d.", port);
}

void flow3r_bsp_display_mirror_deinit_all(void) {
    for (int i = 1; i <= 6; i++) {
        flow3r_bsp_display_mirror_deinit_port(i);
    }
}

bool flow3r_bsp_display_mirror_is_active(int port) {
    if (port < 1 || port > 6) {
        for (int i = 1; i <= 6; i++) {
            if (mirror_ports[i].active) return true;
        }
        return false;
    }
    return mirror_ports[port].active;
}
