# Debug variant: leaves USB-OTG unused so the ESP32-S3's built-in
# USB-Serial-JTAG bridge stays connected to the USB-C port.
list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_ENABLE_USBDEV=0
    TILDAGON_USB_JTAG_DEBUG=1
)

list(APPEND SDKCONFIG_DEFAULTS
    ${MICROPY_BOARD_DIR}/sdkconfig.usbjtag
)
