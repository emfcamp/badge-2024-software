set(IDF_TARGET esp32s3)


# Additional IDF components
set(IDF_COMPONENTS
    ctx
    st3m
    flow3r_bsp
)
set(EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/../../../../../components/"
)

# Config settings
set(SDKCONFIG_DEFAULTS
    boards/sdkconfig.base
    boards/sdkconfig.usb
    boards/sdkconfig.ble
    boards/sdkconfig.240mhz
    boards/sdkconfig.spiram_sx
    boards/tildagon/sdkconfig.board
)


# Baked-in Python modules
if(NOT MICROPY_FROZEN_MANIFEST)
    set(MICROPY_FROZEN_MANIFEST ${CMAKE_CURRENT_LIST_DIR}/manifest.py)
endif()