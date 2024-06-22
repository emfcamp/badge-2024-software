#pragma once

// st3m_scope implements a basic scope.
//
// The audio subsystem will continuously send the global mixing output result
// into the oscilloscope. User code can decide when to draw said scope.

#include <stdint.h>

#include "flow3r_bsp.h"
#include "st3m_gfx.h"

typedef struct {
    // Scope buffer size, in samples. Currently always 240 (same as screen
    // width).
    size_t buffer_size;

    // Triple-buffering for lockless exchange between free-running writer and
    // reader. The exchange buffer is swapped to/from by the reader/writer
    // whenever they're done with a whole sample buffer.
    int16_t *write_buffer;
    int16_t *exchange_buffer;
    int16_t *read_buffer;

    // Offset where the write handler should write the next sample.
    uint32_t write_head_position;
    int16_t prev_value;
    bool zero_crossing_occurred;
} st3m_scope_t;

// Initialize global scope. Must be performed before any other access to scope
// is attempted.
//
// If initialization fails (eg. due to lack of memory) an error will be
// printed.
void st3m_scope_init(void);

// Write a sound sample to the scope.
void st3m_scope_write(int16_t value);

// Retrieve scope's data buffer. Remains valid until the next
// st3m_scope_get_buffer_x or st3m_scope_draw call. Returns buffer's length.
size_t st3m_scope_get_buffer_x(int16_t **buf);

// Draw the scope at bounding box -120/-120 +120/+120.
//
// The user is responsible for clearing background and setting a color.
void st3m_scope_draw(Ctx *ctx);
