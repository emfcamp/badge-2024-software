# Create an INTERFACE library for our C module.
add_library(usermod_tildagon_pin INTERFACE)

# Add our source files to the lib
target_sources(usermod_tildagon_pin INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_pin.c
    ${CMAKE_CURRENT_LIST_DIR}/pins.c
    ${CMAKE_CURRENT_LIST_DIR}/aw9523b.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_tildagon_pin INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_tildagon_pin)
target_link_libraries(usermod_tildagon_pin INTERFACE ${MICROPY_TARGET})
