#pragma once

#include <stddef.h>
#include <stdint.h>

// Data generated from python_payload, squished into a zlib'd tarball. This is
// used to recover the flash filesystem, and to initially set it up on first
// boot.
//
// This is generated using CMake machinery in components/st3m/CMakeLists.txt and
// a generator script at components/st3m/host-tools/pack-sys.py.
extern const uint8_t st3m_sys_data[];
extern const size_t st3m_sys_data_length;