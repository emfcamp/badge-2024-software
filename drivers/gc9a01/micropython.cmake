# Create an INTERFACE library for our C module.
add_library(usermod_display INTERFACE)

# Add our source files to the lib
target_sources(usermod_display INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/display.c
    ${CMAKE_CURRENT_LIST_DIR}/mp_uctx.c
    
)

target_include_directories(usermod_display INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_display)
