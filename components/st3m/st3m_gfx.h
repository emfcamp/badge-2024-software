#pragma once

#include "freertos/FreeRTOS.h"

// clang-format off
#include "ctx_config.h"
#include "ctx.h"
// clang-format on

typedef enum {
    st3m_gfx_default = 0,
    // bitmask flag over base bpp to turn on OSD, only 16bpp for now will
    // become available for other bitdepths as grayscale rather than color
    // overlays.

    // lock the graphics mode, this makes st3m_gfx_set_mode() a no-op
    st3m_gfx_lock = 1 << 8,

    // directly manipulate target framebuffer instead of having
    // separate rasterization task - this causes the rasterization overhead
    // to occur in the micropython task rather than the graphics rasterization
    // task.
    st3m_gfx_direct_ctx = 1 << 9,

    // enable osd compositing, for a small performance boost
    st3m_gfx_osd = 1 << 10,

    // shallower pipeline, prioritize short time from drawing until shown on
    // screen over frame rate
    st3m_gfx_low_latency = 1 << 11,

    // boost FPS by always reporting readiness for drawing, this gets disabled
    // dynamically if FPS falls <13fps
    st3m_gfx_EXPERIMENTAL_think_per_draw = 1 << 12,

    // pixel-doubling
    st3m_gfx_2x = 1 << 13,
    st3m_gfx_3x = 1 << 14,
    st3m_gfx_4x = st3m_gfx_2x | st3m_gfx_3x,

    // keep track of what is drawn and only redraw the bounding box
    st3m_gfx_smart_redraw = 1 << 15,

    // 4 and 8bpp modes use the configured palette, the palette resides
    // in video ram and is lost upon mode change
    st3m_gfx_1bpp = 1,
    st3m_gfx_2bpp = 2,
    st3m_gfx_4bpp = 4,
    st3m_gfx_8bpp = 8,    // bare 8bpp mode is grayscale
    st3m_gfx_rgb332 = 9,  // variant of 8bpp mode using RGB
    st3m_gfx_sepia = 10,  // grayscale rendering with sepia palette
    st3m_gfx_cool = 11,   // grayscale rendering with cool palette
    st3m_gfx_palette = 15,
    // 16bpp modes have the lowest blit overhead - no osd for now
    st3m_gfx_16bpp = 16,
    st3m_gfx_24bpp = 24,
    // 32bpp modes - are slightly faster at doing compositing, but the memory
    // overhead of higher bitdepths cancels out the overhead of converting back
    // and forth between rgb565 and RGBA8, 24 and 32bit modes are here
    // mostly because it leads to nicer math in python.
    st3m_gfx_32bpp = 32,
} st3m_gfx_mode;

void st3m_gfx_fps_update (void);

// sets the system graphics mode, this is the mode you get to
// when calling st3m_gfx_set_mode(st3m_gfx_default);
void st3m_gfx_set_default_mode(st3m_gfx_mode mode);

// sets the current graphics mode
st3m_gfx_mode st3m_gfx_set_mode(st3m_gfx_mode mode);

// gets the current graphics mode
st3m_gfx_mode st3m_gfx_get_mode(void);

// returns a ctx for drawing at the specified mode/target
// should be paired with a st3m_ctx_end_frame
// normal values are st3m_gfx_default and st3m_gfx_osd for base framebuffer
// and overlay drawing context.
Ctx *st3m_gfx_ctx(st3m_gfx_mode mode);

// get the framebuffer associated with graphics mode
// if you ask for st3m_gfx_default you get the current modes fb
// and if you ask for st3m_gfx_osd you get the current modes overlay fb
uint8_t *st3m_gfx_fb(st3m_gfx_mode mode, int *width, int *height, int *stride);

// get the bits per pixel for a given mode
int st3m_gfx_bpp(st3m_gfx_mode mode);

// sets the palette, pal_in is an array with 3 uint8_t's per entry,
// support values for count is 1-256, used only in 4bpp and 8bpp
// graphics modes.
void st3m_gfx_set_palette(uint8_t *pal_in, int count);

// specifies the corners of the clipping rectangle
// for compositing overlay
void st3m_gfx_overlay_clip(int x0, int y0, int x1, int y1);

// returns a running average of fps
float st3m_gfx_fps(void);

// temporary, signature compatible
// with ctx_end_frame()
void st3m_gfx_end_frame(Ctx *ctx);

// Initialize the gfx subsystem of st3m, including the rasterization and
// crtx/blitter pipeline.
void st3m_gfx_init(void);

// Returns true if we right now cannot accept another frame
uint8_t st3m_gfx_pipe_full(void);

// Returns true if there's a free drawlist available to retrieve
uint8_t st3m_gfx_pipe_available(void);

// Flush any in-flight pipelined work, resetting the free ctx/framebuffer queues
// to their initial state. This should be called if there has been any drawlist
// ctx dropped (ie. drawctx_free_get was called but then drawctx_pipe_put
// wasn't, for example if Micropython restarted).
//
// This causes a graphical disturbance and shouldn't be called during normal
// operation. wait_ms is waited for drawlits to clear.
void st3m_gfx_flush(int wait_ms);

typedef struct {
    const char *title;
    const char **lines;
} st3m_gfx_textview_t;

void st3m_gfx_show_textview(st3m_gfx_textview_t *tv);

// Display some text as a splash message. This should be used early on in the
// badge boot process to provide feedback on the rest of the software stack
// coming up
//
// The splash screen is rendered the same way as if submitted by the normal
// drawctx pipe, which means they will get overwritten the moment a proper
// rendering loop starts.
void st3m_gfx_splash(const char *text);

// Draw the flow3r multi-coloured logo at coordinates x,y and with given
// dimension (approx. bounding box size).
void st3m_gfx_flow3r_logo(Ctx *ctx, float x, float y, float dim);

// configure virtual viewport, the default values are 0, 0, 240, 240 which
// also gives room for a copy of the fb for separate rasterize/blit in 16bpp
//
// with, height: width and height of virtual framebuffer
//
// changing the viewport should be done after setting the graphics mode - upon
// graphics mode setting viewport is reset to 240, 240, 0,0,0,0
void st3m_gfx_fbconfig(int width, int height, int blit_x, int blit_y);

// get fbconfig values, arguments passed NULL ptrs are ignored.
void st3m_gfx_get_fbconfig(int *width, int *height, int *blit_x, int *blit_y);
