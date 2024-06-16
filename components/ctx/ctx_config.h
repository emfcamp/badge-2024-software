#pragma once

#include <stdint.h>

#ifdef SIMULATOR
#define CONFIG_FLOW3R_CTX_FLAVOUR_FULL
#else
#include "sdkconfig.h"
#endif

#ifndef __clang__
#if CONFIG_FLOW3R_CTX_FLAVOUR_FULL
#pragma GCC optimize("Oz")
#else
#pragma GCC optimize("Oz")
#endif
#endif

// set this to 1 for faster 8bpp mode - with some glitching
#define CTX_NATIVE_GRAYA8             0

// this might also limit max texture sizes, increasing it
// causes performance drop, so kept just above what we need


#define CTX_DITHER                         1
#define CTX_PROTOCOL_U8_COLOR              1
#define CTX_LIMIT_FORMATS                  1
#define CTX_32BIT_SEGMENTS                 0
#define CTX_RASTERIZER                     1
#define CTX_RASTERIZER_AA                  3
#define CTX_ENABLE_RGB565                  1
#define CTX_ENABLE_RGB565_BYTESWAPPED      1
#define CTX_COMPOSITING_GROUPS             0
#define CTX_ALWAYS_USE_NEAREST_FOR_SCALE1  1
#define CTX_EVENTS                         0
#define CTX_THREADS                        0
#define CTX_TILED                          0
#define CTX_BAREMETAL                      1
#define CTX_ONE_FONT_ENGINE                1

#define CTX_MAX_SCANLINE_LENGTH            960
#define CTX_MAX_JOURNAL_SIZE               (1024*512)
// is also max and limits complexity
// of paths that can be filled
#define CTX_MIN_EDGE_LIST_SIZE             1024

#define CTX_MAX_DASHES                     32
#define CTX_MAX_GRADIENT_STOPS             10
#define CTX_MAX_STATES                     10
#define CTX_MAX_EDGES                      255
#define CTX_MAX_PENDING                    64

#define CTX_GRADIENT_CACHE_ELEMENTS        128
#define CTX_RASTERIZER_MAX_CIRCLE_SEGMENTS 64
#define CTX_MAX_KEYDB                      16
#define CTX_MAX_TEXTURES                   32
#define CTX_PARSER_MAXLEN                  512
#define CTX_PARSER_FIXED_TEMP              1
#define CTX_STRINGPOOL_SIZE                256
#define CTX_MAX_DEVICES                    1
#define CTX_MAX_KEYBINDINGS                16
#define CTX_MAX_CBS                        8
#define CTX_MAX_LISTEN_FDS                 1
#define CTX_HASH_COLS                      5
#define CTX_HASH_ROWS                      5
#define CTX_STROKE_1PX                     1


#if defined(CONFIG_FLOW3R_CTX_FLAVOUR_FULL)
#define CTX_COMPOSITE_O3                1
#define CTX_RASTERIZER_O2               0
#define CTX_GSTATE_PROTECT              1
#define CTX_FORCE_INLINES               1
#define CTX_FRAGMENT_SPECIALIZE         1
#define CTX_ENABLE_YUV420               1
#define CTX_ENABLE_RGBA8                1
#define CTX_ENABLE_RGB332               1
#define CTX_ENABLE_RGB8                 1
#define CTX_ENABLE_GRAY8                1
#define CTX_ENABLE_GRAYA8               1
#define CTX_ENABLE_GRAY1                1
#define CTX_ENABLE_GRAY2                1
#define CTX_ENABLE_GRAY4                1
#define CTX_STB_IMAGE                   1
#define STBI_ONLY_PNG
#define STBI_ONLY_GIF
#define STBI_ONLY_JPEG

#else
#define CTX_COMPOSITE_O3                1
#define CTX_RASTERIZER_O2               0
#define CTX_GSTATE_PROTECT              1
#define CTX_FORCE_INLINES               1
#define CTX_FRAGMENT_SPECIALIZE         1
#define CTX_ENABLE_YUV420               1
#define CTX_ENABLE_RGBA8                1
#define CTX_ENABLE_RGB332               1
#define CTX_ENABLE_RGB8                 1
#define CTX_ENABLE_GRAY8                1
#define CTX_ENABLE_GRAYA8               1
#define CTX_ENABLE_GRAY1                1
#define CTX_ENABLE_GRAY2                1
#define CTX_ENABLE_GRAY4                1
#define CTX_STB_IMAGE                   1
#define STBI_ONLY_PNG
#define STBI_ONLY_GIF
#define STBI_ONLY_JPEG

#endif




#define CTX_STATIC_FONT(font) \
  ctx_load_font_ctx(ctx_font_##font##_name, \
                    ctx_font_##font,       \
                    sizeof (ctx_font_##font))



#define CTX_MAX_FONTS 10

#include "Arimo-Regular.h"
#define CTX_FONT_0 CTX_STATIC_FONT(Arimo_Regular)

#if defined(CONFIG_FLOW3R_CTX_FLAVOUR_FULL)

#include "Arimo-Bold.h"
#include "Arimo-Italic.h"
#include "Arimo-BoldItalic.h"
#define CTX_FONT_1 CTX_STATIC_FONT(Arimo_Bold)
#define CTX_FONT_2 CTX_STATIC_FONT(Arimo_Italic)
#define CTX_FONT_3 CTX_STATIC_FONT(Arimo_BoldItalic)

// #include "CampFont1/CampFont1.h"
// #include "CampFont2/CampFont2.h"
// #include "CampFont3/CampFont3.h"
// #define CTX_FONT_4 CTX_STATIC_FONT(CampFont1)
// #define CTX_FONT_5 CTX_STATIC_FONT(CampFont2)
// #define CTX_FONT_6 CTX_STATIC_FONT(CampFont3)

#include "MaterialIcons.h"
#define CTX_FONT_7 CTX_STATIC_FONT(MaterialIcons)

#include "Comic-Mono.h"
#define CTX_FONT_8 CTX_STATIC_FONT(Comic_Mono)

#include "EMFCampHeading/EMFCampHeading1.h"
#include "EMFCampLabel/EMFCampLabel1.h"
#define CTX_FONT_9 CTX_STATIC_FONT(EMFCampHeading1)
#define CTX_FONT_10 CTX_STATIC_FONT(EMFCampLabel1)


#endif
