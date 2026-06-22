BADGE_DIR := $(abspath $(USERMOD_DIR)/../..)

# This only executes when compiling under Emscripten for the WASM based
# firmware as (amongst other things) ctx uses EM_ASM under Emscripten which
# requires gnu11

ifdef JSFLAGS

SRC_USERMOD_C += $(USERMOD_DIR)/mp_uctx.c

SRC_USERMOD_LIB_C += $(BADGE_DIR)/components/ctx/ctx.c

CFLAGS_USERMOD += -I$(BADGE_DIR)/components/ctx
CFLAGS_USERMOD += -I$(BADGE_DIR)/components/ctx/fonts
CFLAGS_USERMOD += -I$(USERMOD_DIR)
CFLAGS_USERMOD += -I$(USERMOD_DIR)/wasm_stubs
CFLAGS_USERMOD += -DSIMULATOR
CFLAGS_USERMOD += -Wno-typedef-redefinition
CFLAGS_USERMOD += -Wno-double-promotion

EXPORTED_FUNCTIONS_EXTRA += ,\
	_ctx_host,\
	_get_fb,\
	_ctx_wasm_queue_key_event

# This bumps the Emscripten Asyncify stack size otherwise we immediately run
# into issues with the firmware running out of memory in the browser
JSFLAGS += -s ASYNCIFY_STACK_SIZE=65536

$(BUILD)/$(BADGE_DIR)/components/ctx/ctx.o: $(BADGE_DIR)/components/ctx/ctx.c
	$(ECHO) "CC $<"
	$(Q)$(CC) $(filter-out -std=c99,$(CFLAGS)) -std=gnu11 \
		-Wno-deprecated-pragma \
		-Wno-unused-variable \
		-Wno-unused-but-set-variable \
		-Wno-double-promotion \
		-Wno-float-conversion \
		-Wno-tautological-overlap-compare \
		-Wno-incompatible-function-pointer-types \
		-Wno-unused-function \
		-c -MD -MF $(@:.o=.d) -o $@ $<

endif
