
#include "ctx_config.h"


#define FLOW3R_CTX_FLAVOUR_SMOL 1

#ifdef CONFIG_FLOW3R_CTX_FLAVOUR_FULL

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#endif

#define CTX_IMPLEMENTATION
#include "ctx.h"
