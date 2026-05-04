# Create an INTERFACE library for our C module.
add_library(usermod_tildagon_helpers INTERFACE)

# Add our source files to the lib
target_sources(usermod_tildagon_helpers INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_helpers.c
)


# Pull out include paths from components :(
idf_component_get_property(wpa_supplicant_includes wpa_supplicant INCLUDE_DIRS)
idf_component_get_property(wpa_supplicant_dir wpa_supplicant COMPONENT_DIR)
list(TRANSFORM wpa_supplicant_includes PREPEND ${wpa_supplicant_dir}/)
list(APPEND INCLUDES ${wpa_supplicant_includes})

idf_component_get_property(esp_https_ota_includes esp_https_ota INCLUDE_DIRS)
idf_component_get_property(esp_https_ota_dir esp_https_ota COMPONENT_DIR)
list(TRANSFORM esp_https_ota_includes PREPEND ${esp_https_ota_dir}/)
list(APPEND INCLUDES ${esp_https_ota_includes})


idf_component_get_property(esp_http_client_includes esp_http_client INCLUDE_DIRS)
idf_component_get_property(esp_http_client_dir esp_http_client COMPONENT_DIR)
list(TRANSFORM esp_http_client_includes PREPEND ${esp_http_client_dir}/)
list(APPEND INCLUDES ${esp_http_client_includes})

target_include_directories(usermod_tildagon_helpers INTERFACE ${INCLUDES})


# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_tildagon_helpers)


