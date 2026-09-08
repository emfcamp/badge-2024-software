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
    { 40, 39, 41, 42 },         // Port 1: SCK=40, MOSI=39, CS=41, DC=42
    { 36, 35, 37, 38 },         // Port 2: SCK=36, MOSI=35, CS=37, DC=38
    { 33, 34, 47, 48 },         // Port 3: SCK=33, MOSI=34, CS=47, DC=48
    { 14, 11, 13, 12 },         // Port 4: SCK=14, MOSI=11, CS=13, DC=12
    { 16, 18, 15, 17 },         // Port 5: SCK=16, MOSI=18, CS=15, DC=17
    {  4,  3,  5,  6 },         // Port 6: SCK=4,  MOSI=3,  CS=5,  DC=6
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
    flow3r_bsp_display_driver_t driver;
    spi_device_handle_t spi;
} mirror_port_state_t;

static mirror_port_state_t mirror_ports[7];
static bool spi2_bus_inited = false;
static int spi2_active_port = -1;
static int spi2_active_sck = -1;
static int spi2_active_mosi = -1;
static int spi2_user_count = 0;



// ----------------------------------------------------------------------------
// Low-Level LCD Command Helpers
// ----------------------------------------------------------------------------

void flow3r_bsp_display_lcd_send_cmd(spi_device_handle_t spi, int cs_pin, int dc_pin, uint8_t cmd) {
    if (spi == NULL) return;
    if (cs_pin >= 0) gpio_set_level(cs_pin, 0);
    if (dc_pin >= 0) gpio_set_level(dc_pin, 0); // Command mode

    spi_transaction_t t;
    memset(&t, 0, sizeof(t));
    t.flags = SPI_TRANS_USE_TXDATA;
    t.length = 8;
    t.tx_data[0] = cmd;
    spi_device_polling_transmit(spi, &t);
}

void flow3r_bsp_display_lcd_send_data(spi_device_handle_t spi, int cs_pin, int dc_pin, const uint8_t *data, size_t len) {
    if (spi == NULL || data == NULL || len == 0) return;
    if (cs_pin >= 0) gpio_set_level(cs_pin, 0);
    if (dc_pin >= 0) gpio_set_level(dc_pin, 1); // Data mode

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
}

void flow3r_bsp_display_exec_cmds(spi_device_handle_t spi, int cs_pin, int dc_pin, const flow3r_bsp_lcd_cmd_t *cmds, size_t count) {
    if (spi == NULL || cmds == NULL || count == 0) return;
    for (size_t i = 0; i < count; i++) {
        flow3r_bsp_display_lcd_send_cmd(spi, cs_pin, dc_pin, cmds[i].cmd);
        if (cmds[i].data != NULL && cmds[i].data_len > 0) {
            flow3r_bsp_display_lcd_send_data(spi, cs_pin, dc_pin, cmds[i].data, cmds[i].data_len);
        }
        if (cmds[i].delay_ms > 0) {
            vTaskDelay(pdMS_TO_TICKS(cmds[i].delay_ms));
        }
    }
}

void flow3r_bsp_display_driver_free(flow3r_bsp_display_driver_t *driver) {
    if (driver == NULL || !driver->is_allocated) return;
    if (driver->init_seq) {
        for (size_t i = 0; i < driver->init_seq_len; i++) {
            if (driver->init_seq[i].data) free((void *)driver->init_seq[i].data);
        }
        free((void *)driver->init_seq);
    }
    if (driver->prefix_seq) {
        for (size_t i = 0; i < driver->prefix_seq_len; i++) {
            if (driver->prefix_seq[i].data) free((void *)driver->prefix_seq[i].data);
        }
        free((void *)driver->prefix_seq);
    }
    if (driver->postfix_seq) {
        for (size_t i = 0; i < driver->postfix_seq_len; i++) {
            if (driver->postfix_seq[i].data) free((void *)driver->postfix_seq[i].data);
        }
        free((void *)driver->postfix_seq);
    }
    if (driver->header) {
        free((void *)driver->header);
    }
    memset(driver, 0, sizeof(*driver));
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

    // 2. Prefix commands (e.g. for GC9A01 LCD window/RAMWR)
    if (mp->driver.prefix_seq != NULL && mp->driver.prefix_seq_len > 0) {
        flow3r_bsp_display_exec_cmds(mp->spi, mp->cs_pin, mp->dc_pin, mp->driver.prefix_seq, mp->driver.prefix_seq_len);
        if (mp->dc_pin >= 0) {
            gpio_set_level(mp->dc_pin, 1); // Switch to Data mode
        }
    }

    // 3. Transmit magic header if configured (e.g. "TDHD" for HDMI)
    if (mp->driver.header != NULL && mp->driver.header_len > 0) {
        spi_transaction_t tx_hdr;
        memset(&tx_hdr, 0, sizeof(tx_hdr));
        tx_hdr.length = mp->driver.header_len * 8;
        tx_hdr.tx_buffer = mp->driver.header;
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

    // 5. Postfix commands (e.g. e-ink refresh trigger or latch)
    if (mp->driver.postfix_seq != NULL && mp->driver.postfix_seq_len > 0) {
        flow3r_bsp_display_exec_cmds(mp->spi, mp->cs_pin, mp->dc_pin, mp->driver.postfix_seq, mp->driver.postfix_seq_len);
    }

    // 6. Deassert CS HIGH only after entire frame transfer is complete
    if (mp->cs_pin >= 0) {
        gpio_set_level(mp->cs_pin, 1);
    }
}

// ----------------------------------------------------------------------------
// Public API
// ----------------------------------------------------------------------------

static esp_err_t mirror_init_pins(int sck_pin, int mosi_pin, int cs_pin, int dc_pin) {
    ESP_LOGI(TAG, "Configuring SPI mirror pins on SCK=%d, MOSI=%d, CS=%d, DC=%d",
             sck_pin, mosi_pin, cs_pin, dc_pin);

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
        for (int i = 1; i <= 6; i++) {
            if (mirror_ports[i].active && mirror_ports[i].spi != NULL) {
                spi_bus_remove_device(mirror_ports[i].spi);
                mirror_ports[i].spi = NULL;
            }
        }
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

esp_err_t flow3r_bsp_display_mirror_attach(int port, int sck, int mosi, int cs, int dc, int baudrate, const flow3r_bsp_display_driver_t *driver) {
    flow3r_bsp_display_init();
    if (port < 1 || port > 6) {
        ESP_LOGE(TAG, "Invalid hexpansion port %d (must be 1..6)", port);
        return ESP_ERR_INVALID_ARG;
    }

    // Since SPI2_HOST is shared and can only route to one port's pins at a time,
    // deinit all active mirror ports before setting up the new port.
    flow3r_bsp_display_mirror_deinit_all();

    mirror_port_state_t *mp = &mirror_ports[port];

    if (driver != NULL) {
        mp->driver = *driver;
    } else {
        memset(&mp->driver, 0, sizeof(mp->driver));
    }

    const flow3r_bsp_port_pins_t *p = &PORT_PINS[port];
    if (sck < 0) sck = p->sck;
    if (mosi < 0) mosi = p->mosi;
    if (cs < 0) cs = p->cs;
    if (dc < 0) dc = p->dc;

    esp_err_t ret = mirror_init_pins(sck, mosi, cs, dc);
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
    mp->active = true;

    // Run init sequence if present
    if (mp->driver.init_seq != NULL && mp->driver.init_seq_len > 0) {
        if (cs >= 0) gpio_set_level(cs, 0);
        flow3r_bsp_display_exec_cmds(mp->spi, mp->cs_pin, mp->dc_pin, mp->driver.init_seq, mp->driver.init_seq_len);
        if (dc >= 0) gpio_set_level(dc, 1);
        if (cs >= 0) gpio_set_level(cs, 1);
    }

    // Register with generic dynamic display sink subsystem
    flow3r_bsp_display_sink_t sink = {
        .send_frame = mirror_sink_send_frame,
        .user_data = mp,
    };
    mp->sink_handle = flow3r_bsp_display_register_sink(&sink);

    ESP_LOGI(TAG, "Display mirror attached on port %d [SCK=%d, MOSI=%d, CS=%d, DC=%d] (sink handle: %d).",
             port, sck, mosi, cs, dc, mp->sink_handle);
    return ESP_OK;
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
        gpio_set_level(mp->cs_pin, 1);
        gpio_reset_pin(mp->cs_pin);
        mp->cs_pin = -1;
    }
    if (mp->dc_pin >= 0) {
        gpio_reset_pin(mp->dc_pin);
        mp->dc_pin = -1;
    }

    flow3r_bsp_display_driver_free(&mp->driver);

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
