#include "py/runtime.h"
#include "st3m_gfx.h"
#include "flow3r_bsp.h"
#include "mp_uctx.h"
#include "flow3r_bsp_display_mirror.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

#include "esp_log.h"
#include "esp_heap_caps.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"

static const char *TAG = "display";

bool gfx_inited = false;

static mp_obj_t bsp_init() {
    flow3r_bsp_display_init();
    return MP_ROM_QSTR(MP_QSTR_sample);
}
static MP_DEFINE_CONST_FUN_OBJ_0(bsp_init_obj, bsp_init);

static mp_obj_t gfx_init() {
    if (!gfx_inited) {
        st3m_gfx_init();
        gfx_inited = true;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(gfx_init_obj, gfx_init);

static mp_obj_t get_fps() {
    return mp_obj_new_float(st3m_gfx_fps());
}
static MP_DEFINE_CONST_FUN_OBJ_0(get_fps_obj, get_fps);

#define TILDAGON_DISPLAY_WIDTH  240
#define TILDAGON_DISPLAY_HEIGHT 240

EXT_RAM_BSS_ATTR
static uint8_t tildagon_fb[TILDAGON_DISPLAY_WIDTH * TILDAGON_DISPLAY_HEIGHT * 2];
static Ctx *tildagon_ctx = NULL;

Ctx *tildagon_gfx_ctx(void)
{
  flow3r_bsp_display_init();
  if (tildagon_ctx == NULL)
  {
    tildagon_ctx = ctx_new_for_framebuffer (tildagon_fb, TILDAGON_DISPLAY_WIDTH, TILDAGON_DISPLAY_HEIGHT, TILDAGON_DISPLAY_WIDTH * 2, CTX_FORMAT_RGB565_BYTESWAPPED);
  }
  return tildagon_ctx;
}

void tildagon_start_frame(Ctx *ctx)
{
  int32_t offset_x = TILDAGON_DISPLAY_WIDTH / 2;
  int32_t offset_y = TILDAGON_DISPLAY_HEIGHT / 2;

  ctx_save (ctx);
  ctx_identity (ctx);
  ctx_apply_transform (ctx, 1.0f, 0.0f, offset_x, 0.0f, 1.0f, offset_y, 0.0f, 0.0f, 1.0f);
}

static mp_obj_t get_ctx() {
    Ctx *ctx = tildagon_gfx_ctx();
    assert (ctx);
    tildagon_start_frame (ctx);
    return mp_ctx_from_ctx(ctx);
}
static MP_DEFINE_CONST_FUN_OBJ_0(get_ctx_obj, get_ctx);

void tildagon_blit_fb (void)
{
  flow3r_bsp_display_send_fb(tildagon_fb, 16);
  
  // Dispatch to all registered auxiliary display sinks (HDMI mirror, secondary screens, virtual sinks)
  flow3r_bsp_display_dispatch_sinks(tildagon_fb, sizeof(tildagon_fb));
}

void tildagon_end_frame(Ctx *ctx)
{
  ctx_restore (ctx);
  tildagon_blit_fb ();
  // display.end_frame() cannot call ctx_end_frame() directly here: that resets
  // rasterizer state, including the framebuffer clip bounds, which leaves
  // subsequent frames blank. Advance only the texture eviction clock.
  ctx_set_textureclock (ctx, ctx_textureclock (ctx) + 1);
  st3m_gfx_fps_update ();
}

static mp_obj_t end_frame(mp_obj_t ctx) {
    mp_ctx_obj_t *self = MP_OBJ_TO_PTR(ctx);
    tildagon_end_frame (self->ctx);
    return ctx;
}
static MP_DEFINE_CONST_FUN_OBJ_1(end_frame_obj, end_frame);

static mp_obj_t get_framebuffer() {
    return mp_obj_new_bytes(tildagon_fb, sizeof(tildagon_fb));
}
static MP_DEFINE_CONST_FUN_OBJ_0(get_framebuffer_obj, get_framebuffer);

// ----------------------------------------------------------------------------
// Mirror API (Multi-Port Support with Generic Driver Descriptors)
// ----------------------------------------------------------------------------

static flow3r_bsp_lcd_cmd_t *parse_cmd_sequence(mp_obj_t list_obj, size_t *count_out) {
    if (list_obj == mp_const_none) {
        *count_out = 0;
        return NULL;
    }
    size_t len = 0;
    mp_obj_t *items = NULL;
    if (mp_obj_is_type(list_obj, &mp_type_list)) {
        mp_obj_list_get(list_obj, &len, &items);
    } else if (mp_obj_is_type(list_obj, &mp_type_tuple)) {
        mp_obj_tuple_get(list_obj, &len, &items);
    } else {
        *count_out = 0;
        return NULL;
    }
    if (len == 0 || items == NULL) {
        *count_out = 0;
        return NULL;
    }
    flow3r_bsp_lcd_cmd_t *cmds = calloc(len, sizeof(flow3r_bsp_lcd_cmd_t));
    if (!cmds) {
        *count_out = 0;
        return NULL;
    }
    for (size_t i = 0; i < len; i++) {
        if (mp_obj_is_int(items[i])) {
            cmds[i].cmd = (uint8_t)mp_obj_get_int(items[i]);
            cmds[i].data = NULL;
            cmds[i].data_len = 0;
            cmds[i].delay_ms = 0;
        } else if (mp_obj_is_type(items[i], &mp_type_tuple) || mp_obj_is_type(items[i], &mp_type_list)) {
            size_t t_len = 0;
            mp_obj_t *t_items = NULL;
            if (mp_obj_is_type(items[i], &mp_type_tuple)) {
                mp_obj_tuple_get(items[i], &t_len, &t_items);
            } else {
                mp_obj_list_get(items[i], &t_len, &t_items);
            }
            if (t_len >= 1 && t_items) cmds[i].cmd = (uint8_t)mp_obj_get_int(t_items[0]);
            if (t_len >= 2 && t_items && t_items[1] != mp_const_none) {
                mp_buffer_info_t bufinfo;
                if (mp_get_buffer(t_items[1], &bufinfo, MP_BUFFER_READ)) {
                    if (bufinfo.len > 0) {
                        uint8_t *copy = malloc(bufinfo.len);
                        if (copy) {
                            memcpy(copy, bufinfo.buf, bufinfo.len);
                            cmds[i].data = copy;
                            cmds[i].data_len = bufinfo.len;
                        }
                    }
                } else if (mp_obj_is_type(t_items[1], &mp_type_list)) {
                    size_t d_len = 0;
                    mp_obj_t *d_items;
                    mp_obj_list_get(t_items[1], &d_len, &d_items);
                    if (d_len > 0) {
                        uint8_t *copy = malloc(d_len);
                        if (copy) {
                            for (size_t j = 0; j < d_len; j++) {
                                copy[j] = (uint8_t)mp_obj_get_int(d_items[j]);
                            }
                            cmds[i].data = copy;
                            cmds[i].data_len = d_len;
                        }
                    }
                }
            }
            if (t_len >= 3 && t_items) {
                cmds[i].delay_ms = (uint16_t)mp_obj_get_int(t_items[2]);
            }
        }
    }
    *count_out = len;
    return cmds;
}

static mp_obj_t attach_mirror(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    int port = 1;
    int baudrate = 0;
    int sck = -1;
    int mosi = -1;
    int cs = -1;
    int dc = -1;
    mp_obj_t driver_obj = mp_const_none;
    bool raw_specified = false;
    bool raw_val = false;

    if (n_args >= 1) port = mp_obj_get_int(pos_args[0]);
    if (n_args >= 2) baudrate = mp_obj_get_int(pos_args[1]);
    if (n_args >= 3) {
        // Can be raw bool or driver obj
        if (mp_obj_is_bool(pos_args[2])) {
            raw_specified = true;
            raw_val = mp_obj_is_true(pos_args[2]);
        } else {
            driver_obj = pos_args[2];
        }
    }
    if (n_args >= 4) sck = mp_obj_get_int(pos_args[3]);
    if (n_args >= 5) mosi = mp_obj_get_int(pos_args[4]);
    if (n_args >= 6) cs = mp_obj_get_int(pos_args[5]);
    if (n_args >= 7) dc = mp_obj_get_int(pos_args[6]);

    if (kw_args != NULL) {
        for (size_t i = 0; i < kw_args->alloc; i++) {
            if (mp_map_slot_is_filled(kw_args, i)) {
                const char *k = mp_obj_str_get_str(kw_args->table[i].key);
                mp_obj_t v = kw_args->table[i].value;
                if (strcmp(k, "port") == 0) port = mp_obj_get_int(v);
                else if (strcmp(k, "baudrate") == 0) baudrate = mp_obj_get_int(v);
                else if (strcmp(k, "driver") == 0) driver_obj = v;
                else if (strcmp(k, "raw") == 0) {
                    raw_specified = true;
                    raw_val = mp_obj_is_true(v);
                }
                else if (strcmp(k, "sck") == 0) sck = mp_obj_get_int(v);
                else if (strcmp(k, "mosi") == 0) mosi = mp_obj_get_int(v);
                else if (strcmp(k, "cs") == 0) cs = mp_obj_get_int(v);
                else if (strcmp(k, "dc") == 0) dc = mp_obj_get_int(v);
            }
        }
    }

    const flow3r_bsp_display_driver_t *driver_to_use = NULL;
    flow3r_bsp_display_driver_t custom_driver;
    memset(&custom_driver, 0, sizeof(custom_driver));

    if (driver_obj != mp_const_none) {
        if (mp_obj_is_str(driver_obj)) {
            const char *dname = mp_obj_str_get_str(driver_obj);
            if (strcmp(dname, "gc9a01") == 0) {
                driver_to_use = &flow3r_bsp_display_driver_gc9a01;
            } else if (strcmp(dname, "hdmi") == 0) {
                driver_to_use = &flow3r_bsp_display_driver_hdmi;
            } else {
                driver_to_use = &flow3r_bsp_display_driver_raw;
            }
        } else if (mp_obj_is_type(driver_obj, &mp_type_dict)) {
            mp_obj_dict_t *dict = MP_OBJ_TO_PTR(driver_obj);
            custom_driver.is_allocated = true;
            for (size_t i = 0; i < dict->map.alloc; i++) {
                if (mp_map_slot_is_filled(&dict->map, i)) {
                    const char *key = mp_obj_str_get_str(dict->map.table[i].key);
                    mp_obj_t val = dict->map.table[i].value;

                    if (strcmp(key, "init") == 0 || strcmp(key, "init_sequence") == 0) {
                        custom_driver.init_seq = parse_cmd_sequence(val, &custom_driver.init_seq_len);
                    } else if (strcmp(key, "prefix") == 0 || strcmp(key, "frame_prefix") == 0) {
                        custom_driver.prefix_seq = parse_cmd_sequence(val, &custom_driver.prefix_seq_len);
                    } else if (strcmp(key, "postfix") == 0 || strcmp(key, "frame_postfix") == 0) {
                        custom_driver.postfix_seq = parse_cmd_sequence(val, &custom_driver.postfix_seq_len);
                    } else if (strcmp(key, "header") == 0) {
                        mp_buffer_info_t hbuf;
                        if (mp_get_buffer(val, &hbuf, MP_BUFFER_READ) && hbuf.len > 0) {
                            uint8_t *hcopy = malloc(hbuf.len);
                            if (hcopy) {
                                memcpy(hcopy, hbuf.buf, hbuf.len);
                                custom_driver.header = hcopy;
                                custom_driver.header_len = hbuf.len;
                            }
                        }
                    } else if (strcmp(key, "baudrate") == 0 && baudrate <= 0) {
                        baudrate = mp_obj_get_int(val);
                    }
                }
            }
            driver_to_use = &custom_driver;
        }
    } else if (raw_specified) {
        driver_to_use = raw_val ? &flow3r_bsp_display_driver_gc9a01 : &flow3r_bsp_display_driver_hdmi;
    } else {
        driver_to_use = &flow3r_bsp_display_driver_hdmi; // Safe default with HDMI sync header
    }

    // Default baudrates if not explicitly specified
    if (baudrate <= 0) {
        if (driver_to_use == &flow3r_bsp_display_driver_gc9a01) {
            baudrate = 40000000;
        } else {
            baudrate = 10000000;
        }
    }

    esp_err_t err = flow3r_bsp_display_mirror_attach(port, sck, mosi, cs, dc, baudrate, driver_to_use);
    if (err != ESP_OK) {
        mp_raise_OSError(err);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_KW(attach_mirror_obj, 0, attach_mirror);

static mp_obj_t detach_mirror(size_t n_args, const mp_obj_t *args) {
    int port = 0;
    if (n_args >= 1) {
        port = mp_obj_get_int(args[0]);
    }
    if (port <= 0) {
        flow3r_bsp_display_mirror_deinit_all();
    } else {
        flow3r_bsp_display_mirror_deinit_port(port);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(detach_mirror_obj, 0, 1, detach_mirror);

static mp_obj_t is_mirror_active(size_t n_args, const mp_obj_t *args) {
    int port = 0;
    if (n_args >= 1) {
        port = mp_obj_get_int(args[0]);
    }
    return mp_obj_new_bool(flow3r_bsp_display_mirror_is_active(port));
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(is_mirror_active_obj, 0, 1, is_mirror_active);

static mp_obj_t display_get_port_pins(mp_obj_t port_in) {
    int port = mp_obj_get_int(port_in);
    const flow3r_bsp_port_pins_t *p = flow3r_bsp_display_get_port_pins(port);
    if (!p) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid hexpansion port (must be 1..6)"));
    }
    mp_obj_dict_t *d = mp_obj_new_dict(4);
    mp_obj_dict_store(MP_OBJ_FROM_PTR(d), mp_obj_new_str("sck", 3), mp_obj_new_int(p->sck));
    mp_obj_dict_store(MP_OBJ_FROM_PTR(d), mp_obj_new_str("mosi", 4), mp_obj_new_int(p->mosi));
    mp_obj_dict_store(MP_OBJ_FROM_PTR(d), mp_obj_new_str("cs", 2), mp_obj_new_int(p->cs));
    mp_obj_dict_store(MP_OBJ_FROM_PTR(d), mp_obj_new_str("dc", 2), mp_obj_new_int(p->dc));
    return MP_OBJ_FROM_PTR(d);
}
static MP_DEFINE_CONST_FUN_OBJ_1(display_get_port_pins_obj, display_get_port_pins);

// ----------------------------------------------------------------------------
// Secondary Display Object (display.Screen / display.SecondaryDisplay)
// ----------------------------------------------------------------------------

typedef struct _mp_display_screen_obj_t {
    mp_obj_base_t base;
    uint8_t port;
    uint16_t width;
    uint16_t height;
    int baudrate;
    int cs_pin;
    int dc_pin;
    bool raw;
    bool active;
    uint8_t *fb;
    size_t fb_size;
    Ctx *ctx;
    spi_device_handle_t spi;
} mp_display_screen_obj_t;

extern const mp_obj_type_t display_screen_type;

static uint8_t screen_tdhd_header[4] WORD_ALIGNED_ATTR = { 'T', 'D', 'H', 'D' };

static mp_obj_t mp_display_screen_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *all_args) {
    int port = 1;
    int width = 240;
    int height = 240;
    int baudrate = 40000000;
    bool raw = false;
    int sck = -1;
    int mosi = -1;
    int cs = -1;
    int dc = -1;

    if (n_args >= 1) port = mp_obj_get_int(all_args[0]);
    if (n_args >= 2) width = mp_obj_get_int(all_args[1]);
    if (n_args >= 3) height = mp_obj_get_int(all_args[2]);
    if (n_args >= 4) baudrate = mp_obj_get_int(all_args[3]);
    if (n_args >= 5) raw = mp_obj_is_true(all_args[4]);
    if (n_args >= 6) sck = mp_obj_get_int(all_args[5]);
    if (n_args >= 7) mosi = mp_obj_get_int(all_args[6]);
    if (n_args >= 8) cs = mp_obj_get_int(all_args[7]);
    if (n_args >= 9) dc = mp_obj_get_int(all_args[8]);

    for (size_t i = 0; i < n_kw; i++) {
        qstr key = mp_obj_str_get_qstr(all_args[n_args + 2 * i]);
        mp_obj_t val = all_args[n_args + 2 * i + 1];
        const char *key_str = qstr_str(key);
        if (strcmp(key_str, "port") == 0) port = mp_obj_get_int(val);
        else if (strcmp(key_str, "width") == 0) width = mp_obj_get_int(val);
        else if (strcmp(key_str, "height") == 0) height = mp_obj_get_int(val);
        else if (strcmp(key_str, "baudrate") == 0) baudrate = mp_obj_get_int(val);
        else if (strcmp(key_str, "raw") == 0) raw = mp_obj_is_true(val);
        else if (strcmp(key_str, "sck") == 0) sck = mp_obj_get_int(val);
        else if (strcmp(key_str, "mosi") == 0) mosi = mp_obj_get_int(val);
        else if (strcmp(key_str, "cs") == 0) cs = mp_obj_get_int(val);
        else if (strcmp(key_str, "dc") == 0) dc = mp_obj_get_int(val);
    }

    if (port < 1 || port > 6) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid hexpansion port (must be 1..6)"));
    }
    if (width <= 0 || height <= 0 || width > 1024 || height > 1024) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid screen dimensions"));
    }
    if (baudrate <= 0) baudrate = 40000000;

    const flow3r_bsp_port_pins_t *p = flow3r_bsp_display_get_port_pins(port);
    if (!p) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid hexpansion port"));
    }

    if (sck < 0) sck = p->sck;
    if (mosi < 0) mosi = p->mosi;
    if (cs < 0) cs = p->cs;
    if (dc < 0) dc = p->dc;

    mp_display_screen_obj_t *self = m_new_obj(mp_display_screen_obj_t);
    self->base.type = &display_screen_type;
    self->port = port;
    self->width = width;
    self->height = height;
    self->baudrate = baudrate;
    self->raw = raw;
    self->active = false;
    self->spi = NULL;
    self->cs_pin = cs;
    self->dc_pin = dc;

    // Allocate framebuffer in PSRAM
    self->fb_size = width * height * 2;
    self->fb = (uint8_t *)heap_caps_malloc(self->fb_size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!self->fb) {
        self->fb = (uint8_t *)malloc(self->fb_size);
    }
    if (!self->fb) {
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("failed to allocate screen framebuffer"));
    }
    memset(self->fb, 0, self->fb_size);

    // Create Ctx instance
    self->ctx = ctx_new_for_framebuffer(self->fb, width, height, width * 2, CTX_FORMAT_RGB565_BYTESWAPPED);
    if (!self->ctx) {
        free(self->fb);
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("failed to create ctx for screen"));
    }

    // Configure CS pin (idle HIGH)
    if (self->cs_pin >= 0) {
        gpio_config_t cs_cfg = {
            .pin_bit_mask = (1ULL << self->cs_pin),
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&cs_cfg);
        gpio_set_level(self->cs_pin, 1);
    }

    // Configure DC pin (idle HIGH)
    if (self->dc_pin >= 0) {
        gpio_config_t dc_cfg = {
            .pin_bit_mask = (1ULL << self->dc_pin),
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_ENABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&dc_cfg);
        gpio_set_level(self->dc_pin, 1);
    }

    flow3r_bsp_display_init();
    esp_err_t ret = flow3r_bsp_display_spi_acquire_pins(port, sck, mosi, baudrate, &self->spi);
    if (ret != ESP_OK) {
        ctx_destroy(self->ctx);
        free(self->fb);
        mp_raise_OSError(ret);
    }

    // If driving raw GC9A01 LCD panel, wake up and init address window
    if (self->raw) {
        flow3r_bsp_display_lcd_init_gc9a01(self->spi, self->cs_pin, self->dc_pin);
    }

    self->active = true;
    ESP_LOGI(TAG, "Screen created on port %d (%dx%d @ %d Hz, raw=%d)",
             port, width, height, baudrate, (int)raw);
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t mp_display_screen_get_ctx(mp_obj_t self_in) {
    mp_display_screen_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->active || !self->ctx) {
        mp_raise_ValueError(MP_ERROR_TEXT("screen is closed/deinitialized"));
    }

    int32_t offset_x = self->width / 2;
    int32_t offset_y = self->height / 2;

    ctx_save(self->ctx);
    ctx_identity(self->ctx);
    ctx_apply_transform(self->ctx, 1.0f, 0.0f, offset_x, 0.0f, 1.0f, offset_y, 0.0f, 0.0f, 1.0f);
    return mp_ctx_from_ctx(self->ctx);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mp_display_screen_get_ctx_obj, mp_display_screen_get_ctx);

static mp_obj_t mp_display_screen_end_frame(size_t n_args, const mp_obj_t *args) {
    mp_display_screen_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (!self->active || !self->spi || !self->fb) {
        return mp_const_none;
    }

    if (n_args > 1) {
        mp_ctx_obj_t *ctx_obj = MP_OBJ_TO_PTR(args[1]);
        ctx_restore(ctx_obj->ctx);
    } else if (self->ctx) {
        ctx_restore(self->ctx);
    }

    // 1. Assert CS LOW
    if (self->cs_pin >= 0) {
        gpio_set_level(self->cs_pin, 0);
    }

    // 2. If raw LCD, reset address window and send RAMWR while holding CS LOW
    if (self->raw && self->dc_pin >= 0) {
        static const uint8_t c_win[] = { 0x00, 0x00, 0x00, 0xef };
        flow3r_bsp_display_lcd_send_cmd(self->spi, self->cs_pin, self->dc_pin, 0x2a);
        flow3r_bsp_display_lcd_send_data(self->spi, self->cs_pin, self->dc_pin, c_win, sizeof(c_win));
        flow3r_bsp_display_lcd_send_cmd(self->spi, self->cs_pin, self->dc_pin, 0x2b);
        flow3r_bsp_display_lcd_send_data(self->spi, self->cs_pin, self->dc_pin, c_win, sizeof(c_win));
        flow3r_bsp_display_lcd_send_cmd(self->spi, self->cs_pin, self->dc_pin, 0x2c);
        gpio_set_level(self->dc_pin, 1); // Switch to Data mode (CS remains LOW!)
    }

    // 3. Transmit magic header if framed
    if (!self->raw) {
        spi_transaction_t tx_hdr;
        memset(&tx_hdr, 0, sizeof(tx_hdr));
        tx_hdr.length = 4 * 8;
        tx_hdr.tx_buffer = screen_tdhd_header;
        spi_device_polling_transmit(self->spi, &tx_hdr);
    }

    // 4. Transmit pixel data via DMA in chunks while holding CS LOW
    const uint8_t *src = self->fb;
    size_t remaining = self->fb_size;
    while (remaining > 0) {
        size_t chunk = (remaining > 4096) ? 4096 : remaining;
        spi_transaction_t tx_data;
        memset(&tx_data, 0, sizeof(tx_data));
        tx_data.length = chunk * 8;
        tx_data.tx_buffer = src;
        spi_device_polling_transmit(self->spi, &tx_data);
        src += chunk;
        remaining -= chunk;
    }

    // 5. Deassert CS HIGH only after entire frame transfer is complete
    if (self->cs_pin >= 0) {
        gpio_set_level(self->cs_pin, 1);
    }

    if (self->ctx) {
        ctx_set_textureclock(self->ctx, ctx_textureclock(self->ctx) + 1);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mp_display_screen_end_frame_obj, 1, 2, mp_display_screen_end_frame);

static mp_obj_t mp_display_screen_get_framebuffer(mp_obj_t self_in) {
    mp_display_screen_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (!self->fb) {
        return mp_const_none;
    }
    return mp_obj_new_bytes(self->fb, self->fb_size);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mp_display_screen_get_framebuffer_obj, mp_display_screen_get_framebuffer);

static mp_obj_t mp_display_screen_deinit(mp_obj_t self_in) {
    mp_display_screen_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->active) {
        if (self->spi) {
            flow3r_bsp_display_spi_release(self->spi);
            self->spi = NULL;
        }
        if (self->cs_pin >= 0) {
            gpio_set_level(self->cs_pin, 1);
            gpio_reset_pin(self->cs_pin);
            self->cs_pin = -1;
        }
        if (self->dc_pin >= 0) {
            gpio_reset_pin(self->dc_pin);
            self->dc_pin = -1;
        }
        if (self->ctx) {
            ctx_destroy(self->ctx);
            self->ctx = NULL;
        }
        if (self->fb) {
            free(self->fb);
            self->fb = NULL;
        }
        self->active = false;
        ESP_LOGI(TAG, "Screen on port %d closed/deinitialized.", self->port);
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mp_display_screen_deinit_obj, mp_display_screen_deinit);

static void mp_display_screen_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    mp_display_screen_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (dest[0] == MP_OBJ_NULL) {
        const char *attr_str = qstr_str(attr);
        if (strcmp(attr_str, "width") == 0) {
            dest[0] = mp_obj_new_int(self->width);
        } else if (strcmp(attr_str, "height") == 0) {
            dest[0] = mp_obj_new_int(self->height);
        } else if (strcmp(attr_str, "port") == 0) {
            dest[0] = mp_obj_new_int(self->port);
        } else if (strcmp(attr_str, "active") == 0) {
            dest[0] = mp_obj_new_bool(self->active);
        } else {
            dest[1] = MP_OBJ_SENTINEL; // Look in locals dict
        }
    } else if (dest[1] != MP_OBJ_NULL) {
        mp_raise_msg(&mp_type_AttributeError, MP_ERROR_TEXT("attributes are read-only"));
    }
}

static const mp_rom_map_elem_t display_screen_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_get_ctx), MP_ROM_PTR(&mp_display_screen_get_ctx_obj) },
    { MP_ROM_QSTR(MP_QSTR_end_frame), MP_ROM_PTR(&mp_display_screen_end_frame_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_framebuffer), MP_ROM_PTR(&mp_display_screen_get_framebuffer_obj) },
    { MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&mp_display_screen_deinit_obj) },
    { MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&mp_display_screen_deinit_obj) },
};
static MP_DEFINE_CONST_DICT(display_screen_locals_dict, display_screen_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    display_screen_type,
    MP_QSTR_Screen,
    MP_TYPE_FLAG_NONE,
    make_new, mp_display_screen_make_new,
    attr, mp_display_screen_attr,
    locals_dict, &display_screen_locals_dict
);

// ----------------------------------------------------------------------------
// Builtin Demo Graphics
// ----------------------------------------------------------------------------

static mp_obj_t splash() {
    for (int i = 0; i < 5; i++) {
        st3m_gfx_splash("");
    }
    return MP_ROM_QSTR(MP_QSTR_sample);
}
static MP_DEFINE_CONST_FUN_OBJ_0(splash_obj, splash);

static mp_obj_t hexagon(size_t n_args, const mp_obj_t *args) {
    mp_ctx_obj_t *ctx = MP_OBJ_TO_PTR(args[0]);
    float x = mp_obj_get_float(args[1]);
    float y = mp_obj_get_float(args[2]);
    float dim = mp_obj_get_float(args[3]);
    
    float minor_component = cos(M_PI / 3);
    float major_component = sin(M_PI / 3);
    
    ctx_save(ctx->ctx);
    ctx_translate (ctx->ctx, x, y);
    ctx_scale (ctx->ctx, dim, dim);
    ctx_rotate(ctx->ctx, M_PI / 2.0f);
    ctx_move_to(ctx->ctx, -minor_component, -major_component);
    ctx_rel_line_to(ctx->ctx, 1.0f, 0.0f);
    ctx_rel_line_to(ctx->ctx, minor_component, major_component);
    ctx_rel_line_to(ctx->ctx, -minor_component, major_component);
    ctx_rel_line_to(ctx->ctx, -1.0f, 0.0f);
    ctx_rel_line_to(ctx->ctx, -minor_component, -major_component);
    ctx_rel_line_to(ctx->ctx, minor_component, -major_component);
    ctx_fill(ctx->ctx);
    ctx_restore(ctx->ctx);

    return args[0];
}
static MP_DEFINE_CONST_FUN_OBJ_VAR(hexagon_obj, 4, hexagon);

// ----------------------------------------------------------------------------
// Display Module Globals Table
// ----------------------------------------------------------------------------

static const mp_rom_map_elem_t display_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_display) },
    { MP_ROM_QSTR(MP_QSTR_gfx_init), MP_ROM_PTR(&gfx_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_bsp_init), MP_ROM_PTR(&bsp_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_splash), MP_ROM_PTR(&splash_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_fps), MP_ROM_PTR(&get_fps_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_ctx), MP_ROM_PTR(&get_ctx_obj) },
    { MP_ROM_QSTR(MP_QSTR_end_frame), MP_ROM_PTR(&end_frame_obj) },
    { MP_ROM_QSTR(MP_QSTR_hexagon), MP_ROM_PTR(&hexagon_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_framebuffer), MP_ROM_PTR(&get_framebuffer_obj) },
    { MP_ROM_QSTR(MP_QSTR_attach_mirror), MP_ROM_PTR(&attach_mirror_obj) },
    { MP_ROM_QSTR(MP_QSTR_detach_mirror), MP_ROM_PTR(&detach_mirror_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_mirror_active), MP_ROM_PTR(&is_mirror_active_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_port_pins), MP_ROM_PTR(&display_get_port_pins_obj) },

    // Secondary Screen Class & Alias
    { MP_ROM_QSTR(MP_QSTR_Screen), MP_ROM_PTR(&display_screen_type) },
    { MP_ROM_QSTR(MP_QSTR_SecondaryDisplay), MP_ROM_PTR(&display_screen_type) },
};
static MP_DEFINE_CONST_DICT(display_module_globals, display_module_globals_table);

const mp_obj_module_t display_user_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&display_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_display, display_user_module);
