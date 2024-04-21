# Add custom hardware drivers here

# Add the display driver
include(${CMAKE_CURRENT_LIST_DIR}/gc9a01/micropython.cmake)

# Add the HID interface
include(${CMAKE_CURRENT_LIST_DIR}/tildagon_usb/tildagon_usb.cmake)
