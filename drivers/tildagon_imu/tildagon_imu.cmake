# Create an INTERFACE library for our C module.
add_library(usermod_tildagon_imu INTERFACE)


# Add our source files to the lib
target_sources(usermod_tildagon_imu INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_imu.c
    ${CMAKE_CURRENT_LIST_DIR}/lsm6ds3/lsm6ds3.c
    ${CMAKE_CURRENT_LIST_DIR}/mp_imu.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_tildagon_imu INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/lsm6ds3
    ${CMAKE_CURRENT_LIST_DIR}/../../components/st3m
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_tildagon_imu)

