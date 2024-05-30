# Create an INTERFACE library for our C module.
add_library(usermod_tildagon INTERFACE)

# Add our source files to the lib
target_sources(usermod_tildagon INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_tildagon INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod_tildagon INTERFACE usermod_tildagon_hmac)
target_link_libraries(usermod INTERFACE usermod_tildagon)
