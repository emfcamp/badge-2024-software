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

# Pull out include paths from components :(
idf_component_get_property(ctx_includes ctx INCLUDE_DIRS)
idf_component_get_property(ctx_dir ctx COMPONENT_DIR)
list(TRANSFORM ctx_includes PREPEND ${ctx_dir}/)
list(APPEND INCLUDES ${ctx_includes})

idf_component_get_property(flow3r_bsp_includes flow3r_bsp INCLUDE_DIRS)
idf_component_get_property(flow3r_bsp_dir flow3r_bsp COMPONENT_DIR)
list(TRANSFORM flow3r_bsp_includes PREPEND ${flow3r_bsp_dir}/)
list(APPEND INCLUDES ${flow3r_bsp_includes})

target_include_directories(usermod_display INTERFACE ${INCLUDES})


# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_display)
