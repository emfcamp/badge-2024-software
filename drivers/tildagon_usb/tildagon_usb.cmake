# Create an INTERFACE library for our C module.
add_library(usermod_tildagon_usb INTERFACE)

# Add our source files to the lib
target_sources(usermod_tildagon_usb INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_usb.c
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_hid_host.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_tildagon_usb INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_tildagon_usb INTERFACE "-DLOG_LOCAL_LEVEL=ESP_LOG_VERBOSE")

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_tildagon_usb)