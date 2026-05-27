# Create an INTERFACE library for our C module.
add_library(usermod_tildagon_frontboard INTERFACE)


# Add our source files to the lib
target_sources(usermod_tildagon_frontboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_frontboard.c
    ${CMAKE_CURRENT_LIST_DIR}/cy8cmbrx/cy8cmbrx.c
    ${CMAKE_CURRENT_LIST_DIR}/mp_frontboard.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_tildagon_frontboard INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/cy8cmbrx
    ${CMAKE_CURRENT_LIST_DIR}/../tildagon_imu/qmc6309
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_tildagon_frontboard)