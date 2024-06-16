
#include "ctx_config.h"


#define FLOW3R_CTX_FLAVOUR_SMOL 1


#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#ifdef CONFIG_FLOW3R_CTX_FLAVOUR_FULL
#endif

int mp_ctx_vfs_load_file (const char     *path,
                          unsigned char **contents,
                          long           *length,
                          long            max_length);
#define CTX_LOAD_FILE mp_ctx_vfs_load_file

#define CTX_IMPLEMENTATION
#include "ctx.h"
