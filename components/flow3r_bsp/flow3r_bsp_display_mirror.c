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

// Use a dedicated host, NOT the one the main gc9a01 screen driver permanently
// owns with its own fixed pins (flow3r_bsp_display.c's gc9a01_config.host,
// which is the numeric literal 2 -- i.e. SPI3_HOST, since spi_host_device_t is
// zero-indexed: SPI1_HOST=0, SPI2_HOST=1, SPI3_HOST=2. NOT SPI2_HOST, despite
// the "2" in its name -- an earlier fix here mistook that literal for
// SPI2_HOST and pointed the mirror at SPI3_HOST too, which collided directly
// with the main screen instead of avoiding it).
// spi_bus_initialize() binds one fixed pin set per host for its lifetime, so
// sharing a host between the main screen and a hexpansion mirror (different
// pins) causes whichever one initializes second to fail its own
// spi_bus_add_device()/spi_bus_initialize() call. SPI2_HOST is the one
// GP-SPI peripheral left unused (SPI1_HOST is permanently reserved for
// flash/PSRAM), giving the mirror a fully independent peripheral.
#define MIRROR_SPI_HOST         SPI2_HOST
#define MIRROR_MAX_XFER         (115200 + 128)
#define MIRROR_CHUNK_BYTES      4096

// High-speed SPI pins for hexpansion ports 1..6 based on Tildagon v1.1 schematic
// (Port HS lines connected directly to ESP32-S3 GPIOs).
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

bool flow3r_bsp_display_pin_ok(int pin, bool need_output) {
    if (pin < 0) return true; // Sentinel for unused/default pin
    if (pin >= GPIO_NUM_MAX) return false;
    if (need_output && !GPIO_IS_VALID_OUTPUT_GPIO(pin)) return false;
    if (!GPIO_IS_VALID_GPIO(pin)) return false;
    // Reserved on Tildagon ESP32-S3:
    // Native GC9A01 LCD: 1, 2, 7, 8
    // USB-JTAG: 19, 20
    // SPI flash / PSRAM: 26..32
    // Console UART: 43, 44
    // Host I2C: 45, 46
    static const int reserved[] = { 1, 2, 7, 8, 19, 20, 26, 27, 28, 29, 30, 31, 32, 43, 44, 45, 46 };
    for (size_t i = 0; i < sizeof(reserved) / sizeof(reserved[0]); i++) {
        if (pin == reserved[i]) return false;
    }
    return true;
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

static mirror_port_state_t mirror_ports[7] = {
    { .cs_pin = -1, .dc_pin = -1, .sink_handle = -1 },
    { .cs_pin = -1, .dc_pin = -1, .sink_handle = -1 },
    { .cs_pin = -1, .dc_pin = -1, .sink_handle = -1 },
    { .cs_pin = -1, .dc_pin = -1, .sink_handle = -1 },
    { .cs_pin = -1, .dc_pin = -1, .sink_handle = -1 },
    { .cs_pin = -1, .dc_pin = -1, .sink_handle = -1 },
    { .cs_pin = -1, .dc_pin = -1, .sink_handle = -1 },
};

static bool spi2_bus_inited = false;
static int spi2_active_sck = -1;
static int spi2_active_mosi = -1;
static int spi2_user_count = 0;

static bool port_claimed[7];

esp_err_t flow3r_bsp_display_port_claim(int port) {
    if (port < 1 || port > 6) return ESP_ERR_INVALID_ARG;
    if (port_claimed[port]) {
        ESP_LOGE(TAG, "port %d is already in use by another mirror or Screen", port);
        return ESP_ERR_INVALID_STATE;
    }
    port_claimed[port] = true;
    return ESP_OK;
}

void flow3r_bsp_display_port_release(int port) {
    if (port >= 1 && port <= 6) port_claimed[port] = false;
}



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
    if (driver == NULL) return;
    if (driver->is_allocated) {
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
    }
    memset(driver, 0, sizeof(*driver));
}

static esp_err_t mirror_tx_blob(spi_device_handle_t spi, const uint8_t *src, size_t len) {
    while (len > 0) {
        size_t chunk = (len > MIRROR_CHUNK_BYTES) ? MIRROR_CHUNK_BYTES : len;
        spi_transaction_t t;
        memset(&t, 0, sizeof(t));
        t.length = chunk * 8;
        t.tx_buffer = src;
        esp_err_t ret = spi_device_polling_transmit(spi, &t);
        if (ret != ESP_OK) return ret;
        src += chunk;
        len -= chunk;
    }
    return ESP_OK;
}

// ----------------------------------------------------------------------------
// Frame Sink Callback (Invoked on every display.end_frame)
// ----------------------------------------------------------------------------

static void mirror_sink_send_frame(const void *fb_data, size_t len, void *user_data) {
    mirror_port_state_t *mp = (mirror_port_state_t *)user_data;
    if (mp == NULL || !mp->active || mp->spi == NULL || fb_data == NULL || len == 0) {
        return;
    }

    // NOTE (2026-09-13): spi_device_acquire_bus() in this ESP-IDF version
    // (v5.5.1) hard-rejects any wait value other than portMAX_DELAY with
    // ESP_ERR_INVALID_ARG (see SPI_CHECK at the top of the function in
    // esp_driver_spi/src/gpspi/spi_master.c). A prior session's attempt to
    // bound this wait with a 1s timeout was silently failing every single
    // frame send with that error -- not the hang it was meant to diagnose.
    esp_err_t bret = spi_device_acquire_bus(mp->spi, portMAX_DELAY);
    if (bret != ESP_OK) {
        static bool had_acquire_err = false;
        if (!had_acquire_err) {
            ESP_LOGE(TAG, "mirror_sink_send_frame: spi_device_acquire_bus failed/timed out: %s", esp_err_to_name(bret));
            had_acquire_err = true;
        }
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
        esp_err_t hret = spi_device_polling_transmit(mp->spi, &tx_hdr);
        if (hret != ESP_OK) {
            static bool had_hdr_err = false;
            if (!had_hdr_err) {
                ESP_LOGE(TAG, "mirror header tx failed: %s", esp_err_to_name(hret));
                had_hdr_err = true;
            }
        }
    }

    // 4. Transmit pixel payload via SPI DMA while holding CS LOW
    esp_err_t tret = mirror_tx_blob(mp->spi, (const uint8_t *)fb_data, len);
    if (tret != ESP_OK) {
        static bool had_frame_err = false;
        if (!had_frame_err) {
            ESP_LOGE(TAG, "mirror frame tx failed: %s", esp_err_to_name(tret));
            had_frame_err = true;
        }
    }

    // 5. Postfix commands (e.g. e-ink refresh trigger or latch)
    if (mp->driver.postfix_seq != NULL && mp->driver.postfix_seq_len > 0) {
        flow3r_bsp_display_exec_cmds(mp->spi, mp->cs_pin, mp->dc_pin, mp->driver.postfix_seq, mp->driver.postfix_seq_len);
    }

    // 6. Deassert CS HIGH only after entire frame transfer is complete
    if (mp->cs_pin >= 0) {
        gpio_set_level(mp->cs_pin, 1);
    }

    spi_device_release_bus(mp->spi);
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

    if (!flow3r_bsp_display_pin_ok(sck, true) || !flow3r_bsp_display_pin_ok(mosi, true)) {
        ESP_LOGE(TAG, "Invalid SCK=%d or MOSI=%d pin", sck, mosi);
        return ESP_ERR_INVALID_ARG;
    }

    if (spi2_bus_inited && (spi2_active_sck != sck || spi2_active_mosi != mosi)) {
        if (spi2_user_count > 0) {
            ESP_LOGE(TAG,
                     "SPI2_HOST already routed to SCK=%d MOSI=%d with %d active "
                     "device(s); detach them before switching to SCK=%d MOSI=%d",
                     spi2_active_sck, spi2_active_mosi, spi2_user_count, sck, mosi);
            return ESP_ERR_INVALID_STATE;
        }
        esp_err_t fret = spi_bus_free(MIRROR_SPI_HOST);
        if (fret != ESP_OK) {
            ESP_LOGE(TAG, "spi_bus_free failed: %s", esp_err_to_name(fret));
            return fret;
        }
        spi2_bus_inited = false;
    }

    if (!spi2_bus_inited) {
        spi_bus_config_t buscfg = {
            .miso_io_num = -1,
            .mosi_io_num = mosi,
            .sclk_io_num = sck,
            .quadwp_io_num = -1,
            .quadhd_io_num = -1,
            .max_transfer_sz = MIRROR_MAX_XFER,
            .flags = SPICOMMON_BUSFLAG_MASTER,
        };

        esp_err_t ret = spi_bus_initialize(MIRROR_SPI_HOST, &buscfg, SPI_DMA_CH_AUTO);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "spi_bus_initialize failed (SCK=%d, MOSI=%d): %s", sck, mosi, esp_err_to_name(ret));
            return ret;
        }
        spi2_bus_inited = true;
        spi2_active_sck = sck;
        spi2_active_mosi = mosi;
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
        esp_err_t ret = spi_bus_free(MIRROR_SPI_HOST);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "spi_bus_free failed: %s", esp_err_to_name(ret));
            return;
        }
        spi2_bus_inited = false;
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

    const flow3r_bsp_port_pins_t *p = &PORT_PINS[port];
    if (sck < 0) sck = p->sck;
    if (mosi < 0) mosi = p->mosi;
    if (cs < 0) cs = p->cs;
    if (dc < 0) dc = p->dc;

    if (!flow3r_bsp_display_pin_ok(sck, true) || !flow3r_bsp_display_pin_ok(mosi, true) ||
        !flow3r_bsp_display_pin_ok(cs, true) || !flow3r_bsp_display_pin_ok(dc, true)) {
        ESP_LOGE(TAG, "Invalid GPIO pins specified for port %d", port);
        return ESP_ERR_INVALID_ARG;
    }

    // Since SPI2_HOST is shared and can only route to one port's pins at a time,
    // deinit all active mirror ports before setting up the new port.
    flow3r_bsp_display_mirror_deinit_all();

    esp_err_t ret = flow3r_bsp_display_port_claim(port);
    if (ret != ESP_OK) {
        return ret;
    }

    // Acquire the SPI bus/device before touching CS/DC GPIO state: this is
    // the step most likely to fail (host already claimed by another SPI
    // user, e.g. this same hexpansion's own onboard driver). If we
    // reconfigured CS/DC first and then failed here, we'd have already
    // stolen those pins out from under whatever driver is currently using
    // them, breaking it even though our own attach never succeeded.
    spi_device_handle_t spi = NULL;
    ret = flow3r_bsp_display_spi_acquire_pins(port, sck, mosi, baudrate, &spi);
    if (ret != ESP_OK) {
        goto fail_claim;
    }

    ret = mirror_init_pins(sck, mosi, cs, dc);
    if (ret != ESP_OK) {
        goto fail_spi;
    }

    mirror_port_state_t *mp = &mirror_ports[port];
    if (driver != NULL) {
        mp->driver = *driver;
    } else {
        memset(&mp->driver, 0, sizeof(mp->driver));
    }
    mp->port = port;
    mp->cs_pin = cs;
    mp->dc_pin = dc;
    mp->spi = spi;
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
    if (mp->sink_handle <= 0) {
        ESP_LOGE(TAG, "Sink registration failed for port %d", port);
        // Hand driver ownership back to caller to prevent double free
        mp->driver.is_allocated = false;
        flow3r_bsp_display_mirror_deinit_port(port);
        return ESP_ERR_NO_MEM;
    }

    ESP_LOGI(TAG, "Display mirror attached on port %d [SCK=%d, MOSI=%d, CS=%d, DC=%d] (sink handle: %d).",
             port, sck, mosi, cs, dc, mp->sink_handle);
    return ESP_OK;

fail_spi:
    if (cs >= 0) gpio_reset_pin(cs);
    if (dc >= 0) gpio_reset_pin(dc);
    flow3r_bsp_display_spi_release(spi);
fail_claim:
    flow3r_bsp_display_port_release(port);
    return ret;
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

    flow3r_bsp_display_port_release(port);
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
