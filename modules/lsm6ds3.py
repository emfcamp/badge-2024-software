# https://www.pololu.com/file/0J1087/LSM6DS33.pdf
# https://github.com/jposada202020/MicroPython_LSM6DSOX/blob/master/micropython_lsm6dsox/lsm6dsox.py
# From Chris Roger's ME35 Page!
# Yoinked from https://github.com/remren/me35/blob/main/hw2/acceltesting/lsm6ds3.py

# Most recently updated as of 9/24/23

import struct
import time

LSM = 0x6B


class LSM6DS3:
    def __init__(self, i2c):
        self.gyro = []
        self.accel = []
        self.i2c = i2c
        print(f"LSM6DS3 Scan: {[hex(i) for i in self.i2c.scan()]}")

    def init_lsm6ds3(self):
        ID = self.i2c.readfrom_mem(LSM, 0x0F, 1)
        time.sleep(0.2)
        ID = struct.unpack("<b", ID)[0]

        rate = {
            "done": 0b0000,
            "12.5": 0b0001,
            "26": 0b0010,
            "52": 0b0011,
            "104": 0b0100,
            "208": 0b0101,
            "416": 0b0110,
            "833": 0b0111,
            "1.66k": 0b1000,
            "3.33k": 0b1001,
            "6.66k": 0b1010,
            "1.6": 0b1011,
        }
        anti_alias = {"400": 0b00, "200": 0b01, "100": 0b10, "50": 0b11}
        XL_range = {"2g": 0b00, "4g": 0b10, "8g": 0b11, "16g": 0b01}
        G_range = {"250": 0b00, "500": 0b01, "1000": 0b10, "2000": 0b11}
        G_125_fullscale = 0

        # XLfactor = (0.061, 0.488, 0.122, 0.244)
        # Gfactor = (8.75, 17.50, 35.0, 70.0)

        # 58 = =high performance, +/- 4g
        XL = (rate["208"] << 4) + (XL_range["4g"] << 2) + anti_alias["400"]
        self.i2c.writeto_mem(LSM, 0x10, struct.pack(">b", XL))  # enable accel

        # 58 = high performance - 1000 dps
        G = (rate["1.66k"] << 4) + (G_range["1000"] << 2) + (G_125_fullscale << 1) + 0
        self.i2c.writeto_mem(LSM, 0x11, struct.pack(">b", G))  # enable gyro

        time.sleep(0.2)

        temp = self.i2c.readfrom_mem(LSM, 0x20, 2)
        temp = struct.unpack("<h", temp)[0]
        temp / 256 + 25.0  # what's the purpose of this?

        gyro = self.i2c.readfrom_mem(LSM, 0x22, 6)
        gyro = struct.unpack("<hhh", gyro)

        accel = self.i2c.readfrom_mem(LSM, 0x28, 6)
        accel = struct.unpack("<hhh", accel)

    def readaccel(self):
        accel = self.i2c.readfrom_mem(LSM, 0x28, 6)
        accel = struct.unpack("<hhh", accel)
        print(accel[0])
        return accel

    def readgyro(self):
        gyro = self.i2c.readfrom_mem(LSM, 0x22, 6)
        gyro = struct.unpack("<hhh", gyro)
        return gyro
