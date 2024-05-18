if (NOT EXISTS "${CMAKE_CURRENT_BINARY_DIR}/include/")
    file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/include/")
endif()

idf_component_register(
    SRCS
    INCLUDE_DIRS
        .
    REQUIRES
        esp_http_client
        esp_https_ota
        mbedtls
        wpa_supplicant
)
