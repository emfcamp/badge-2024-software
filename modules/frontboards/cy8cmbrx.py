from frontboards.cy8cmbrx_defs import CY8CMBRX
from machine import I2C
# from tildagon import ePin


# follow section 6 of https://www.infineon.com/assets/row/public/documents/30/42/infineon-an90071-cy8cmbr3xxx-capsenser-design-guide-applicationnotes-en.pdf
# to configure this.
cy8cmbr3116_config = [
    CY8CMBRX.CS0_ENABLE
    | CY8CMBRX.CS1_ENABLE
    | CY8CMBRX.CS2_ENABLE
    | CY8CMBRX.CS3_ENABLE
    | CY8CMBRX.CS4_ENABLE
    | CY8CMBRX.CS5_ENABLE
    | CY8CMBRX.CS6_ENABLE
    | CY8CMBRX.CS7_ENABLE,  # 0x00 SENSOR_EN LSB
    CY8CMBRX.CS8_ENABLE
    | CY8CMBRX.CS9_ENABLE
    | CY8CMBRX.CS10_ENABLE
    | CY8CMBRX.CS11_ENABLE
    | CY8CMBRX.CS12_ENABLE
    | CY8CMBRX.CS13_ENABLE
    | CY8CMBRX.CS14_ENABLE,  # 0x01 SENSOR_EN MSB
    0x00,  # 0x02 FSS_EN LSB turning these on means only one touch is detected.
    0x00,  # 0x03 FSS_EN MSB
    0x00,  # 0x04 TOGGLE_EN LSB
    0x00,  # 0x05 TOGGLE_EN MSB
    0x00,  # 0x06 LED_ON_EN LSB
    0x00,  # 0x07 LED_ON_EN MSB
    CY8CMBRX.SENS2_X1 | CY8CMBRX.SENS3_X2,  # 0x08 SENSITIVITY0
    CY8CMBRX.SENS0_X3
    | CY8CMBRX.SENS1_X4
    | CY8CMBRX.SENS2_X1
    | CY8CMBRX.SENS3_X2,  # 0x09 SENSITIVITY1
    CY8CMBRX.SENS0_X3
    | CY8CMBRX.SENS1_X4
    | CY8CMBRX.SENS2_X1
    | CY8CMBRX.SENS3_X4,  # 0x0A SENSITIVITY2
    CY8CMBRX.SENS0_X4 | CY8CMBRX.SENS1_X4 | CY8CMBRX.SENS2_X4,  # 0x0B SENSITIVITY3
    0x80,  # 0x0C BASE_THRESHOLD0
    0x80,  # 0x0D BASE_THRESHOLD1
    0x80,  # 0x0E FINGER_THRESHOLD2
    0x80,  # 0x0F FINGER_THRESHOLD3
    0x80,  # 0x10 FINGER_THRESHOLD4
    0x80,  # 0x11 FINGER_THRESHOLD5
    0x80,  # 0x12 FINGER_THRESHOLD6
    0x80,  # 0x13 FINGER_THRESHOLD7
    0x80,  # 0x14 FINGER_THRESHOLD8
    0x80,  # 0x15 FINGER_THRESHOLD9
    0x80,  # 0x16 FINGER_THRESHOLD10
    0x80,  # 0x17 FINGER_THRESHOLD11
    0x80,  # 0x18 FINGER_THRESHOLD12
    0x80,  # 0x19 FINGER_THRESHOLD13
    0x80,  # 0x1A FINGER_THRESHOLD14
    0x7F,  # 0x1B FINGER_THRESHOLD15
    0x03,  # 0x1C SENSOR_DEBOUNCE
    0x00,  # 0x1D BUTTON_HYS
    0x00,  # 0x1E NOT USED
    0x00,  # 0x1F BUTTON_LBR
    0x00,  # 0x20 BUTTON_NNT
    0x00,  # 0x21 BUTTON_NT
    0x00,  # 0x22 NOT USED
    0x00,  # 0x23 NOT USED
    0x00,  # 0x24 NOT USED
    0x00,  # 0x25 NOT USED
    CY8CMBRX.CS0_ENABLE | CY8CMBRX.CS1_ENABLE,  # 0x26 PROX.EN
    0x00,  # 0x27 PROX.CFG
    0x06,  # 0x28 PROX.CFG2
    0x00,  # 0x29 NOT USED
    0x00,  # 0x2A PROX.TOUCH_TH0 LSB
    0x02,  # 0x2B PROX.TOUCH_TH0 MSB
    0x00,  # 0x2C PROX.TOUCH_TH1 LSB
    0x02,  # 0x2D PROX.TOUCH_TH1 MSB
    CY8CMBRX.RES_16_BIT,  # 0x2E PROX.RESOLUTION0
    CY8CMBRX.RES_15_BIT,  # 0x2F PROX.RESOLUTION1
    0x00,  # 0x30 PROX.HYS
    0x00,  # 0x31 NOT USED
    0x00,  # 0x32 PROX.LBR
    0x00,  # 0x33 PROX.NNT
    0x00,  # 0x34 PROX.NT
    0x1E,  # 0x35 PROX.POSITIVE_TH0
    0x1E,  # 0x36 PROX.POSITIVE_TH1
    0x00,  # 0x37 NOT USED
    0x00,  # 0x38 NOT USED
    0x1E,  # 0x39 PROX.NEGATIVE_TH0
    0x1E,  # 0x3A PROX.NEGATIVE_TH1
    0x00,  # 0x3B NOT USED
    0x00,  # 0x3C NOT USED
    0x00,  # 0x3D LED_ON_TIME
    0x01,  # 0x3E BUZZER_CFG
    0x01,  # 0x3F BUZZER_ON_TIME
    0x00,  # 0x40 GPO_CFG
    0xFF,  # 0x41 PWM_DUTYCYCLE_CFG0
    0xFF,  # 0x42 PWM_DUTYCYCLE_CFG1
    0xFF,  # 0x43 PWM_DUTYCYCLE_CFG2
    0xFF,  # 0x44 PWM_DUTYCYCLE_CFG3
    0xFF,  # 0x45 PWM_DUTYCYCLE_CFG4
    0xFF,  # 0x46 PWM_DUTYCYCLE_CFG5
    0xFF,  # 0x47 PWM_DUTYCYCLE_CFG6
    0xFF,  # 0x48 PWM_DUTYCYCLE_CFG7
    0x00,  # 0x49 NOT USED
    0x00,  # 0x4A NOT USED
    0x00,  # 0x4B NOT USED
    0x00,  # 0x4C SPO_CFG
    CY8CMBRX.IIR_EN,  # 0x4D DEVICE_CFG0
    CY8CMBRX.SYSD_EN,  # 0x4E DEVICE_CFG1
    CY8CMBRX.ATH_EN | CY8CMBRX.GUARD_EN,  # 0x4F DEVICE_CFG2
    0x00,  # 0x50 DEVICE_CFG3
    0x37,  # 0x51 I2C_ADDR don't change this!!
    0x01,  # 0x52 REFRESH_CTRL
    0x00,  # 0x53 NOT USED
    0x00,  # 0x54 NOT USED
    0x0A,  # 0x55 STATE_TIMEOUT
    0x00,  # 0x56 NOT USED
    0x00,  # 0x57 NOT USED
    0x00,  # 0x58 NOT USED
    0x00,  # 0x59 NOT USED
    0x00,  # 0x5A NOT USED
    0x00,  # 0x5B NOT USED
    0x00,  # 0x5C NOT USED
    0x00,  # 0x5D SLIDER_CFG
    0x00,  # 0x5E NOT USED
    0x00,  # 0x5F NOT USED
    0x00,  # 0x60 NOT USED
    0x00,  # 0x61 SLIDER1_CFG
    0x00,  # 0x62 SLIDER1_RESOLUTION
    0x00,  # 0x63 SLIDER1_THRESHOLD
    0x00,  # 0x64 NOT USED
    0x00,  # 0x65 NOT USED
    0x00,  # 0x66 NOT USED
    0x00,  # 0x67 SLIDER2_CFG
    0x00,  # 0x68 SLIDER2_RESOLUTION
    0x00,  # 0x69 SLIDER2_THRESHOLD
    0x00,  # 0x6A NOT USED
    0x00,  # 0x6B NOT USED
    0x00,  # 0x6C NOT USED
    0x00,  # 0x6D NOT USED
    0x00,  # 0x6E NOT USED
    0x00,  # 0x6F NOT USED
    0x00,  # 0x70 NOT USED
    0x00,  # 0x71 SLIDER_LBR
    0x00,  # 0x72 SLIDER_NNT
    0x00,  # 0x73 SLIDER_NT
    0x00,  # 0x74 NOT USED
    0x00,  # 0x75 NOT USED
    0x00,  # 0x76 NOT USED
    0x00,  # 0x77 NOT USED
    0x00,  # 0x78 NOT USED
    0x00,  # 0x79 NOT USED
    0x00,  # 0x7A SCRATCHPAD0
    0x00,  # 0x7B SCRATCHPAD1
    0x00,  # 0x7C NOT USED
    0x00,  # 0x7D NOT USED
    # 0x76, #0x7E CRC_LSB - CRC is calculated using 126 bytes above and appended
    # 0xBD  #0X7F CRC_MSB
]


def cy8cmbr3116_init():
    top = I2C(0)
    top.scan()
    device_crc = top.readfrom_mem(0x37, 0x7E, 2)
    # could look for a calibration file and alter the config to apply it
    config_crc = cy8cmbr_crc(cy8cmbr3116_config)
    if device_crc[0] != config_crc[0] or device_crc[1] != config_crc[1]:
        print("configuring touch")
        top.writeto_mem(0x37, 0x00, bytes(cy8cmbr3116_config + config_crc))
        top.writeto_mem(0x37, 0x86, bytes([0x02]))
        import time

        time.sleep(0.5)
        # todo eliminate the sleep? it only happens when the ic needs configuring.


def cy8cmbr_crc(config):
    crc = 0xFFFF
    for byte in config:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    result = [crc & 0xFF, crc >> 8]
    return result
