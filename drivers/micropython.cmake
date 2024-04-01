# Add custom hardware drivers here

# Add the HID interface
include(${CMAKE_CURRENT_LIST_DIR}/tildagon_usb/tildagon_usb.cmake)

# Add TCA9548A I2C MUX
add_library(tildagon INTERFACE)
target_sources(tildagon INTERFACE
  ${CMAKE_CURRENT_LIST_DIR}/tildagon.c
  ${CMAKE_CURRENT_LIST_DIR}/tca9548a.c
)

target_link_libraries(usermod INTERFACE tildagon)
