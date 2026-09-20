#include "flow3r_bsp.h"

#include <string.h>
#include <stdlib.h>

#include "esp_log.h"
#include "sdkconfig.h"

#include "flow3r_bsp_gc9a01.h"

static const char *TAG = "flow3r-bsp-display";

flow3r_bsp_gc9a01_config_t gc9a01_config = {
    .reset_used = 0,
    .backlight_used = 0,

    .pin_sck = 8,
    .pin_mosi = 7,
    .pin_cs = 1,
    .pin_dc = 2,
    .pin_backlight = 0,

    .host = 2,
};

static flow3r_bsp_gc9a01_t gc9a01;
static uint8_t gc9a01_initialized = 0;

void flow3r_bsp_display_init(void) {
    if (gc9a01_initialized) {
        return;
    }
    ESP_LOGI(TAG, "gc9a01 initializing...");
    esp_err_t ret = flow3r_bsp_gc9a01_init(&gc9a01, &gc9a01_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "gc9a01 init failed: %s", esp_err_to_name(ret));
    } else {
        gc9a01_initialized = 1;
        ESP_LOGI(TAG, "gc9a01 initialized");
    }
}

void flow3r_bsp_display_send_fb_osd(void *fb_data, int bits, int scale,
                                    void *osd_data, int osd_x0, int osd_y0,
                                    int osd_x1, int osd_y1) {
    if (!gc9a01_initialized) {
        return;
    }
    static bool had_error = false;

    esp_err_t ret =
        flow3r_bsp_gc9a01_blit_osd(&gc9a01, fb_data, bits, scale, osd_data,
                                   osd_x0, osd_y0, osd_x1, osd_y1);
    if (ret != ESP_OK) {
        if (!had_error) {
            ESP_LOGE(TAG, "display blit failed: %s", esp_err_to_name(ret));
            had_error = true;
        }
    } else {
        if (had_error) {
            ESP_LOGI(TAG, "display blit success!");
            had_error = false;
        }
    }
}

void flow3r_bsp_display_send_fb(void *fb_data, int bits) {
    flow3r_bsp_display_send_fb_osd(fb_data, bits, 1, NULL, 0, 0, 0, 0);
}

void flow3r_bsp_display_send_rect(const void *data,
                                   uint16_t x, uint16_t y,
                                   uint16_t w, uint16_t h) {
    if (!gc9a01_initialized) return;
    esp_err_t ret = flow3r_bsp_gc9a01_blit_rect(&gc9a01, data, x, y, w, h);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "display rect blit failed: %s", esp_err_to_name(ret));
    }
}

void flow3r_bsp_display_set_backlight(uint8_t percent) {
    if (!gc9a01_initialized) {
        return;
    }
    flow3r_bsp_gc9a01_backlight_set(&gc9a01, percent);
}

// ----------------------------------------------------------------------------
// Generic Display Sink Subsystem (Unlimited Dynamic Sinks)
// ----------------------------------------------------------------------------

typedef struct display_sink_node {
    int handle;
    flow3r_bsp_display_sink_t sink;
    struct display_sink_node *next;
} display_sink_node_t;

static display_sink_node_t *sinks_head = NULL;
static int next_sink_handle = 1;
static size_t active_sink_count = 0;

int flow3r_bsp_display_register_sink(const flow3r_bsp_display_sink_t *sink) {
    if (sink == NULL || sink->send_frame == NULL) {
        ESP_LOGW(TAG, "Attempted to register invalid/null display sink.");
        return -1;
    }

    display_sink_node_t *node = (display_sink_node_t *)malloc(sizeof(display_sink_node_t));
    if (node == NULL) {
        ESP_LOGE(TAG, "Failed to allocate memory for display sink node.");
        return -1;
    }

    node->handle = next_sink_handle++;
    node->sink = *sink;
    node->next = sinks_head;
    sinks_head = node;
    active_sink_count++;

    ESP_LOGI(TAG, "Display sink #%d registered (Total active sinks: %u).",
             node->handle, (unsigned int)active_sink_count);
    return node->handle;
}

void flow3r_bsp_display_unregister_sink(int handle) {
    display_sink_node_t *prev = NULL;
    display_sink_node_t *cur = sinks_head;

    while (cur != NULL) {
        if (cur->handle == handle) {
            if (prev == NULL) {
                sinks_head = cur->next;
            } else {
                prev->next = cur->next;
            }
            free(cur);
            if (active_sink_count > 0) active_sink_count--;
            ESP_LOGI(TAG, "Display sink #%d unregistered (Total active sinks: %u).",
                     handle, (unsigned int)active_sink_count);
            return;
        }
        prev = cur;
        cur = cur->next;
    }
}

void flow3r_bsp_display_unregister_all_sinks(void) {
    display_sink_node_t *cur = sinks_head;
    while (cur != NULL) {
        display_sink_node_t *next = cur->next;
        free(cur);
        cur = next;
    }
    sinks_head = NULL;
    active_sink_count = 0;
    ESP_LOGI(TAG, "All display sinks unregistered.");
}

void flow3r_bsp_display_dispatch_sinks(const void *fb_data, size_t len) {
    for (display_sink_node_t *cur = sinks_head; cur != NULL; cur = cur->next) {
        if (cur->sink.send_frame != NULL) {
            cur->sink.send_frame(fb_data, len, cur->sink.user_data);
        }
    }
}

size_t flow3r_bsp_display_get_sink_count(void) {
    return active_sink_count;
}
