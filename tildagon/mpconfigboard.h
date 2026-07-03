#ifndef MICROPY_HW_BOARD_NAME
#ifdef TILDAGON_USB_JTAG_DEBUG
#define MICROPY_HW_BOARD_NAME               "Tildagon (USB-JTAG debug)"
#else
#define MICROPY_HW_BOARD_NAME               "Tildagon"
#endif
#endif
#define MICROPY_HW_MCU_NAME                 "ESP32S3"

// Enable UART REPL for modules that have an external USB-UART and don't use native USB.
#define MICROPY_HW_ENABLE_UART_REPL         (1)

#define MICROPY_HW_I2C0_SCL                 (9)
#define MICROPY_HW_I2C0_SDA                 (8)

#define MICROPY_PY_TILDAGON_I2C             (1)

void tildagon_startup(void);
#define MICROPY_BOARD_STARTUP tildagon_startup