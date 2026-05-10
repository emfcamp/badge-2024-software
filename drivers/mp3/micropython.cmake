add_library(usermod_mp3 INTERFACE)

target_sources(usermod_mp3 INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/mp3module.c
)

target_include_directories(usermod_mp3 INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_options(usermod_mp3 INTERFACE
    -Wno-unused-function
    -Wno-unused-variable
    -Wno-unused-but-set-variable
    -Wno-shift-negative-value
    -Wno-implicit-fallthrough
    -Wno-double-promotion
    -Wno-float-conversion
)

target_link_libraries(usermod INTERFACE usermod_mp3)
