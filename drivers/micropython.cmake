# Add custom hardware drivers here

# Add OTA helpers
include(${CMAKE_CURRENT_LIST_DIR}/tildagon_helpers/micropython.cmake)


# Add the display driver
include(${CMAKE_CURRENT_LIST_DIR}/gc9a01/micropython.cmake)

# Add TCA9548A I2C MUX and micropython machine.I2C bindings
include(${CMAKE_CURRENT_LIST_DIR}/tildagon_i2c/tildagon_i2c.cmake)

# Add PMIC and usb PD and micropython power bindings
include(${CMAKE_CURRENT_LIST_DIR}/tildagon_power/tildagon_power.cmake)

# Add OTA helpers
include(${CMAKE_CURRENT_LIST_DIR}/ota/micropython.cmake)

# Add AW9523B GPIO Expander and micropython tildagon.Pin bindings
include(${CMAKE_CURRENT_LIST_DIR}/tildagon_pin/micropython.cmake)

include(${CMAKE_CURRENT_LIST_DIR}/tildagon/micropython.cmake)

# Add burnt-in HMAC
include(${CMAKE_CURRENT_LIST_DIR}/tildagon_hmac/micropython.cmake)
