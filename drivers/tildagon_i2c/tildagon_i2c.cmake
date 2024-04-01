# Create an INTERFACE library for our C module.
add_library(usermod_tildagon_i2c INTERFACE)

# Add our source files to the lib
target_sources(usermod_tildagon_i2c INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_i2c.c
    ${CMAKE_CURRENT_LIST_DIR}/tca9548a.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_tildagon_i2c INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_tildagon_i2c)
