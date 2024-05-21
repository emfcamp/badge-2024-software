# Create an INTERFACE library for our C module.
add_library(usermod_ota INTERFACE)

# Add our source files to the lib
target_sources(usermod_ota INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/ota.c
)

# I'm sure something is supposed to add this include automatically but I'm not sure what...
#target_include_directories(usermod_ota INTERFACE
#    "$ENV{IDF_PATH}/components/esp_http_client/include"
#    "$ENV{IDF_PATH}/components/esp_https_ota/include"
#    "$MICROPY_PORT_DIR/managed_components/espressif__nghttp"
#)

# Add the current directory as an include directory.
# target_include_directories(usermod_ota INTERFACE
#     ${CMAKE_CURRENT_LIST_DIR}
# )

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_ota)
