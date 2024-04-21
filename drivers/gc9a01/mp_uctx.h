#pragma once

// clang-format off
#include "ctx_config.h"
#include "ctx.h"
// clang-format on

#define STATIC static

typedef struct _mp_ctx_obj_t {
    mp_obj_base_t base;
    Ctx *ctx;
    mp_obj_t user_data;
} mp_ctx_obj_t;

extern const mp_obj_type_t mp_ctx_type;

mp_obj_t mp_ctx_from_ctx(Ctx *ctx);