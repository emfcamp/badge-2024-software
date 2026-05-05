set(IDF_TARGET esp32s3)

cmake_policy(SET CMP0152 OLD)

# Additional IDF components
set(IDF_COMPONENTS
    ctx
    st3m
    flow3r_bmi270
    flow3r_bsp
    tildagon
    esp_https_ota
    wpa_supplicant
)

if(NOT GIT_FOUND)
    find_package(Git QUIET)
endif()

file(
        REAL_PATH
        "../../../../.."
        FIRMWARE_ROOT
        BASE_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
)

set(EXTRA_COMPONENT_DIRS
    "${FIRMWARE_ROOT}/components/"
)


execute_process(
        COMMAND "python" "components/st3m/host-tools/version.py"
        WORKING_DIRECTORY "${FIRMWARE_ROOT}"
        RESULT_VARIABLE res
        OUTPUT_VARIABLE TILDAGON_GIT_VERSION
        OUTPUT_STRIP_TRAILING_WHITESPACE)
set(
    CONFIG_APP_PROJECT_VER
    "${TILDAGON_GIT_VERSION}"
)
message("TILDAGON_GIT_VERSION=${TILDAGON_GIT_VERSION}")
message("Location=${FIRMWARE_ROOT}")
configure_file("${CMAKE_CURRENT_LIST_DIR}/sdkconfig.project_ver.in" "${CMAKE_CURRENT_LIST_DIR}/../../build-tildagon/sdkconfig.project_ver")

# Config settings
set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.ble
    boards/sdkconfig.240mhz
    boards/sdkconfig.spiram_sx
    boards/tildagon/sdkconfig.board
    build-tildagon/sdkconfig.project_ver
)

# Start-up tasks
set(MICROPY_SOURCE_BOARD
    ${MICROPY_BOARD_DIR}/board_init.c
)

# Baked-in Python modules
if(NOT MICROPY_FROZEN_MANIFEST)
    set(MICROPY_FROZEN_MANIFEST ${CMAKE_CURRENT_LIST_DIR}/manifest.py)
endif()

