#include "py/runtime.h"
#include "st3m_gfx.h"
#include "flow3r_bsp.h"
#include "mp_uctx.h"
#include <math.h>

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

//EXT_RAM_BSS_ATTR
static uint8_t tildagon_fb[TILDAGON_DISPLAY_WIDTH * TILDAGON_DISPLAY_HEIGHT * 2];
static Ctx *tildagon_ctx = NULL;

Ctx *tildagon_gfx_ctx(void)
{
  if (tildagon_ctx == NULL)
  {
    tildagon_ctx = ctx_new_for_framebuffer (tildagon_fb, TILDAGON_DISPLAY_WIDTH, TILDAGON_DISPLAY_HEIGHT, TILDAGON_DISPLAY_WIDTH * 2, CTX_FORMAT_RGB565_BYTESWAPPED);
  }
  return tildagon_ctx;
}

void tildagon_start_frame(Ctx *ctx)
{
  int32_t offset_x = FLOW3R_BSP_DISPLAY_WIDTH / 2;
  int32_t offset_y = FLOW3R_BSP_DISPLAY_HEIGHT / 2;

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
}

void tildagon_end_frame(Ctx *ctx)
{
  ctx_restore (ctx);
  tildagon_blit_fb ();
  st3m_gfx_fps_update ();
}

static mp_obj_t end_frame(mp_obj_t ctx) {
    mp_ctx_obj_t *self = MP_OBJ_TO_PTR(ctx);
    tildagon_end_frame (self->ctx);
    return ctx;
}
static MP_DEFINE_CONST_FUN_OBJ_1(end_frame_obj, end_frame);

static mp_obj_t splash() {
    for (int i = 0; i < 5; i++) {
        st3m_gfx_splash("");
    }
    return MP_ROM_QSTR(MP_QSTR_sample);
}
static MP_DEFINE_CONST_FUN_OBJ_0(splash_obj, splash);

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
    ctx_translate (ctx->ctx, x, y);
    ctx_scale (ctx->ctx, dim, dim);
    
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
    { MP_ROM_QSTR(MP_QSTR_bsp_init), MP_ROM_PTR(&bsp_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_splash), MP_ROM_PTR(&splash_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_fps), MP_ROM_PTR(&get_fps_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_ctx), MP_ROM_PTR(&get_ctx_obj) },
    { MP_ROM_QSTR(MP_QSTR_end_frame), MP_ROM_PTR(&end_frame_obj) },
    { MP_ROM_QSTR(MP_QSTR_hexagon), MP_ROM_PTR(&hexagon_obj) },
};
static MP_DEFINE_CONST_DICT(display_module_globals, display_module_globals_table);

const mp_obj_module_t display_user_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&display_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_display, display_user_module);
