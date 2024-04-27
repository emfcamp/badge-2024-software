
#include <stdint.h>
#include "ctx_config.h"
#undef EMSCRIPTEN
#undef CTX_PARSER
#define CTX_PARSER 1
#undef CTX_TILED

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#define CTX_IMPLEMENTATION
#include "ctx.h"
