#pragma once

/* Plain C declarations that don't need the MicroPython object system, so
 * they can be included from non-MicroPython-aware translation units (e.g.
 * board_init.c). See tildagon_pin.h for the full binding. */
extern void tildagon_pins_init( void );
