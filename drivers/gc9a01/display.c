#include "py/runtime.h"
#include "st3m_counter.h"
#include "flow3r_bsp.h"
#include "mp_uctx.h"
#include <math.h>

#include "esp_task.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/idf_additions.h"

static float smoothed_fps = 0.0f;

static st3m_counter_rate_t rast_rate;

static inline void gfx_fps_update(void) {
    st3m_counter_rate_sample(&rast_rate);
    float rate = 1000000.0 / st3m_counter_rate_average(&rast_rate);
    smoothed_fps = smoothed_fps * 0.6 + 0.4 * rate;
}

static bool gfx_inited = false;

static mp_obj_t gfx_init() {
    if (!gfx_inited) {
        st3m_counter_rate_init(&rast_rate);
        flow3r_bsp_display_init();
        gfx_inited = true;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(gfx_init_obj, gfx_init);

static mp_obj_t get_fps() {
    return mp_obj_new_float(smoothed_fps);
}
static MP_DEFINE_CONST_FUN_OBJ_0(get_fps_obj, get_fps);

#define TILDAGON_DISPLAY_WIDTH  240
#define TILDAGON_DISPLAY_HEIGHT 240

static uint8_t tildagon_fb[TILDAGON_DISPLAY_WIDTH * TILDAGON_DISPLAY_HEIGHT * 2] __attribute__((aligned(16)));
static Ctx *tildagon_ctx = NULL;

typedef enum {
    FB_INVALID,
    FB_RENDERED,
    FB_DISPLAYED,
} FramebufferState;
static FramebufferState fb_sect_state[4] = {FB_INVALID, FB_INVALID, FB_INVALID, FB_INVALID};

static portTASK_FUNCTION(vADisplayFlip, pvParameters) {
    for (;;) {
        for (int i = 0; i < 4; i++) {
            while (fb_sect_state[i] != FB_RENDERED) {
                xTaskNotifyWait(0, ULONG_MAX, NULL, portMAX_DELAY);
            }
            flow3r_bsp_display_send_fb(tildagon_fb + (TILDAGON_DISPLAY_WIDTH * TILDAGON_DISPLAY_HEIGHT * 2 / 4) * i, i);
            fb_sect_state[i] = FB_INVALID;
        }
    }
    vTaskDelete(NULL);
}

TaskHandle_t display_flip_task = NULL;

static mp_obj_t start_display_flip_task() {
    xTaskCreatePinnedToCore(vADisplayFlip,
                            "DisplayFlip",
                            2048,
                            NULL,
                            tskIDLE_PRIORITY + 2,
                            &display_flip_task, 0);

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(start_display_flip_task_obj, start_display_flip_task);

static inline Ctx *tildagon_gfx_ctx(void) {
    if (tildagon_ctx == NULL)
    {
        tildagon_ctx = ctx_new_for_framebuffer(tildagon_fb, TILDAGON_DISPLAY_WIDTH, TILDAGON_DISPLAY_HEIGHT, TILDAGON_DISPLAY_WIDTH * 2, CTX_FORMAT_RGB565_BYTESWAPPED);
    }
    return tildagon_ctx;
}

static inline void tildagon_start_frame(Ctx *ctx) {
    int32_t offset_x = FLOW3R_BSP_DISPLAY_WIDTH / 2;
    int32_t offset_y = FLOW3R_BSP_DISPLAY_HEIGHT / 2;

    ctx_save(ctx);
    ctx_identity(ctx);
    ctx_apply_transform(ctx, 1.0f, 0.0f, offset_x, 0.0f, 1.0f, offset_y, 0.0f, 0.0f, 1.0f);
}

static mp_obj_t section_ready(mp_obj_t section) {
    mp_uint_t i = mp_obj_int_get_uint_checked(section);
    return fb_sect_state[i] == FB_INVALID ? mp_const_true : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(section_ready_obj, section_ready);

static mp_obj_t all_sections_ready() {
    return (fb_sect_state[0] == FB_INVALID) &&
           (fb_sect_state[1] == FB_INVALID) &&
           (fb_sect_state[2] == FB_INVALID) &&
           (fb_sect_state[3] == FB_INVALID)
               ? mp_const_true
               : mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_0(all_sections_ready_obj, all_sections_ready);

static mp_obj_t start_frame() {
    Ctx *ctx = tildagon_gfx_ctx();
    assert(ctx);
    tildagon_start_frame(ctx);
    return mp_ctx_from_ctx(ctx);
}
static MP_DEFINE_CONST_FUN_OBJ_0(start_frame_obj, start_frame);

static inline void tildagon_end_frame(Ctx *ctx) {
    ctx_restore(ctx);
    fb_sect_state[0] = FB_RENDERED;
    fb_sect_state[1] = FB_RENDERED;
    fb_sect_state[2] = FB_RENDERED;
    fb_sect_state[3] = FB_RENDERED;
    if (display_flip_task) {
        xTaskNotify(display_flip_task, 0, eNoAction);
    }
    gfx_fps_update();
}

static mp_obj_t end_frame(mp_obj_t ctx) {
    mp_ctx_obj_t *self = MP_OBJ_TO_PTR(ctx);
    tildagon_end_frame(self->ctx);
    return ctx;
}
static MP_DEFINE_CONST_FUN_OBJ_1(end_frame_obj, end_frame);

static mp_obj_t hexagon(size_t n_args, const mp_obj_t *args) {
    // Draw a regular hexagon in a context and return the context
    mp_ctx_obj_t *ctx = MP_OBJ_TO_PTR(args[0]);
    float x = mp_obj_get_float(args[1]);
    float y = mp_obj_get_float(args[2]);
    float dim = mp_obj_get_float(args[3]);

    // All the internal angles are 120 degrees, or 2/3 pi radians
    // This translates to either an offset of (1, 0) or the pair below
    float minor_component = cos(M_PI / 3);
    float major_component = sin(M_PI / 3);

    // Stash the caller's axes
    ctx_save(ctx->ctx);

    // Set the origin to the centre of the hexagon and scale to the size
    ctx_translate(ctx->ctx, x, y);
    ctx_scale(ctx->ctx, dim, dim);

    // Rotate so point is at the top - the drawing code has the flat side at the top
    ctx_rotate(ctx->ctx, M_PI / 2.0f);

    // Move to the start of the top left line
    ctx_move_to(ctx->ctx, -minor_component, -major_component);

    // Draw the six segments
    ctx_rel_line_to(ctx->ctx, 1.0f, 0.0f);
    ctx_rel_line_to(ctx->ctx, minor_component, major_component);
    ctx_rel_line_to(ctx->ctx, -minor_component, major_component);
    ctx_rel_line_to(ctx->ctx, -1.0f, 0.0f);
    ctx_rel_line_to(ctx->ctx, -minor_component, -major_component);
    ctx_rel_line_to(ctx->ctx, minor_component, -major_component);

    // Fill the hexagon
    ctx_fill(ctx->ctx);

    // Restore the axes
    ctx_restore(ctx->ctx);

    // Return the mp version ctx, for chaining
    return args[0];
}
static MP_DEFINE_CONST_FUN_OBJ_VAR(hexagon_obj, 4, hexagon);


static const mp_rom_map_elem_t display_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_display) },
    { MP_ROM_QSTR(MP_QSTR_gfx_init), MP_ROM_PTR(&gfx_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_fps), MP_ROM_PTR(&get_fps_obj) },
    { MP_ROM_QSTR(MP_QSTR_start_frame), MP_ROM_PTR(&start_frame_obj) },
    { MP_ROM_QSTR(MP_QSTR_end_frame), MP_ROM_PTR(&end_frame_obj) },
    { MP_ROM_QSTR(MP_QSTR_start_display_flip_task), MP_ROM_PTR(&start_display_flip_task_obj) },
    { MP_ROM_QSTR(MP_QSTR_section_ready), MP_ROM_PTR(&section_ready_obj) },
    { MP_ROM_QSTR(MP_QSTR_all_sections_ready), MP_ROM_PTR(&all_sections_ready_obj) },
    { MP_ROM_QSTR(MP_QSTR_hexagon), MP_ROM_PTR(&hexagon_obj) },
};
static MP_DEFINE_CONST_DICT(display_module_globals, display_module_globals_table);

const mp_obj_module_t display_user_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&display_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_display, display_user_module);
