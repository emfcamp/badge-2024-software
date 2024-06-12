# A easy to use module for the basic components of the tildagon badge

from tildagonos import tildagonos
from egpio import ePin
import imu as tilda_imu
import math
import time


class led:
    @staticmethod
    def _setup_leds():
        tildagonos.set_led_power(True)

    @staticmethod
    def set(led_number, state):
        if not isinstance(led_number, int) or led_number < 1 or led_number > 12:
            raise ValueError("led_number must be an integer between 1 and 12")

        # TODO : Ideally shouldn't need to run _setup_leds each use of set_led
        led._setup_leds()

        tildagonos.leds[led_number] = state
        tildagonos.leds.write()


class button:
    @staticmethod
    def get(button_letter):
        button_letter = button_letter.lower()
        button_letters = {
            "a": (2, 6),
            "b": (2, 7),
            "c": (1, 0),
            "d": (1, 1),
            "e": (1, 2),
            "f": (1, 3),
        }
        if button_letter in button_letters.keys():
            # Note the button must be flipped, as will return True when not pressed
            return not ePin(button_letters[button_letter]).value()
        else:
            raise ValueError(
                "button_letter must be a string of a single letter from a to f"
            )


class imu:
    class ImuData:
        def __init__(self, x, y, z):
            self.x = x
            self.y = y
            self.z = z

        def __getitem__(self, index):
            if index == 0:
                return self.x
            elif index == 1:
                return self.y
            elif index == 2:
                return self.z
            else:
                raise IndexError("Index out of range. Valid indices are 0, 1, and 2.")

        def __str__(self):
            return f"x: {self.x}, y: {self.y}, z: {self.z}"

    @staticmethod
    def _magnitude(acc_read):
        return math.sqrt(sum(i**2 for i in acc_read))

    @staticmethod
    def is_tilted_forward():
        acc_read = tilda_imu.acc_read()
        if acc_read[0] < -4:
            return True
        return False

    @staticmethod
    def is_tilted_back():
        acc_read = tilda_imu.acc_read()
        if acc_read[0] > 4:
            return True
        return False

    @staticmethod
    def is_tilted_left():
        acc_read = tilda_imu.acc_read()
        if acc_read[1] < -4:
            return True
        return False

    @staticmethod
    def is_tilted_right():
        acc_read = tilda_imu.acc_read()
        if acc_read[1] > 4:
            return True
        return False

    @staticmethod
    def is_shaken():
        acc_read1 = tilda_imu.acc_read()
        magnitude1 = imu._magnitude(acc_read1)

        # Wait for a short period of time before taking another reading
        time.sleep(0.1)

        acc_read2 = tilda_imu.acc_read()
        magnitude2 = imu._magnitude(acc_read2)

        # If the change in magnitude is above a certain threshold (4 for now), the IMU is being shaken
        if abs(magnitude1 - magnitude2) > 4:
            return True
        return False

    @staticmethod
    def get_acceleration():
        raw_data = tilda_imu.acc_read()
        acc_object = imu.ImuData(raw_data[0], raw_data[1], raw_data[2])
        return acc_object
