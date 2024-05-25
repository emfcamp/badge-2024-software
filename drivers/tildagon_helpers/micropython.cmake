# Create an INTERFACE library for our C module.
add_library(usermod_tildagon_helpers INTERFACE)

# Add our source files to the lib
target_sources(usermod_tildagon_helpers INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_helpers.c
)


# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_tildagon_helpers)



# Create an INTERFACE library for our C module.
add_library(usermod_imu INTERFACE)
# Add our source files to the lib
target_sources(usermod_imu INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/mp_imu.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_imu INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/../../components/st3m
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_imu)