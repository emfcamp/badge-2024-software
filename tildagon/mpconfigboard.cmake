set(IDF_TARGET esp32s3)


# Additional IDF components
set(IDF_COMPONENTS
    ctx
    st3m
    flow3r_bmi270
    flow3r_bsp
    tildagon
)
set(EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/../../../../../components/"
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
execute_process(
        COMMAND "python" "components/st3m/host-tools/version.py"
        WORKING_DIRECTORY "${FIRMWARE_ROOT}"
        RESULT_VARIABLE res
        OUTPUT_VARIABLE TILDAGON_GIT_VERSION
        OUTPUT_STRIP_TRAILING_WHITESPACE)
message("TILDAGON_GIT_VERSION=${TILDAGON_GIT_VERSION}")
message("Location=${FIRMWARE_ROOT}")
configure_file("${CMAKE_CURRENT_LIST_DIR}/sdkconfig.project_ver.in" "${CMAKE_CURRENT_LIST_DIR}/../../build-tildagon/sdkconfig.project_ver")

# Config settings
set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.usb
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

