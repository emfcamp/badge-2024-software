# A easy to use module for the basic components of the tildagon badge

from tildagonos import tildagonos
from egpio import ePin
import imu as tilda_imu
import math
import time
import display as hw_display
from app_components import clear_background


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


class BadgeDisplay:
    """Simple display API wrapper with `show`, `clear`, `draw_text`"""

    def show(self, what, delay=0.5):
        # Accept strings, keywords 'happy'/'sad', callables that draw(ctx), or lists for simple animations
        if hasattr(what, "__iter__") and not isinstance(what, str):
            for frame in what:
                self.show(frame, delay=delay)
            return

        ctx = hw_display.get_ctx()
        clear_background(ctx)
        # Accept string keys
        if isinstance(what, str):
            key = what.lower()
        else:
            key = None

        if key:
            handler = IMAGE_HANDLERS.get(key)
            if handler:
                handler(ctx)
            else:
                Image.text(ctx, what if isinstance(what, str) else key)
        elif callable(what):
            # custom draw function that accepts ctx
            what(ctx)
        else:
            # fallback to text representation
            Image.text(ctx, str(what))

        hw_display.end_frame(ctx)
        if delay:
            time.sleep(delay)

    def clear(self):
        ctx = hw_display.get_ctx()
        clear_background(ctx)
        hw_display.end_frame(ctx)

    def draw_text(self, text, delay=0, clear_before=True, initial=True):
        # Draw text in the middle of the screen
        
        # Needed as first text write always fails (draws only first letter) for an unknown reason
        if initial:
            self.draw_text("-", delay=delay, clear_before=clear_before, initial=False)
        ctx = hw_display.get_ctx()
        if clear_before:
            clear_background(ctx)
            #time.sleep(0.05)
            Image.text(ctx, text)
        hw_display.end_frame(ctx)
        if delay:
            time.sleep(delay)


class Image:
    """Image namespace with drawing methods and constants.

    Use like `Image.HAPPY` (constant) or pass `Image.HAPPY` as a callable to `display.show()`.
    """

    @staticmethod
    def _face_base(ctx, x=0, y=0, size=120, face_color=(1, 1, 0), eye_color=(0, 0, 0)):
        ctx.save()
        ctx.translate(x, y)
        r = size / 2
        ctx.rgb(*face_color).arc(0, 0, r, 0, 2 * math.pi, False).fill()

        eye_r = size * 0.06
        eye_x = size * 0.25
        eye_y = -size * 0.15
        ctx.rgb(*eye_color).arc(-eye_x, eye_y, eye_r, 0, 2 * math.pi, False).fill()
        ctx.rgb(*eye_color).arc(eye_x, eye_y, eye_r, 0, 2 * math.pi, False).fill()
    
    @staticmethod
    def _arrow(ctx, size=140):
        # Draw the shaft
        ctx.rgb(1, 1, 1)
        ctx.line_width = size * 0.12
        ctx.begin_path()
        ctx.move_to(0, size * 0.45)
        ctx.line_to(0, -size * 0.12)
        ctx.stroke()

        # Draw a smaller arrowhead
        ctx.begin_path()
        ctx.move_to(0, -size * 0.5)
        ctx.line_to(size * 0.22, -size * 0.1)
        ctx.line_to(-size * 0.22, -size * 0.1)
        ctx.close_path()
        ctx.fill()

    @staticmethod
    def text(ctx, text, x=0, y=0, font_size=24, color=(1, 1, 1), align_center=True):
        ctx.save()
        ctx.font = ctx.get_font_name(0)  # Select a real embedded font
        ctx.font_size = font_size
        if align_center:
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
        ctx.rgb(*color)
        ctx.move_to(x, y).text(text)
        ctx.restore()

    @staticmethod
    def HAPPY(ctx, x=0, y=0, size=160, face_color=(1, 1, 0), eye_color=(0, 0, 0), mouth_color=(0, 0, 0)):
        Image._face_base(ctx, x=x, y=y, size=size, face_color=face_color, eye_color=eye_color)
        ctx.rgb(*mouth_color).arc(0, size * 0.08, size * 0.35, 0.2 * math.pi, 0.8 * math.pi, False).fill()

    @staticmethod
    def SAD(ctx, x=0, y=0, size=160, face_color=(1, 1, 0), eye_color=(0, 0, 0), mouth_color=(0, 0, 0)):
        Image._face_base(ctx, x=x, y=y, size=size, face_color=face_color, eye_color=eye_color)
        ctx.rgb(*mouth_color).arc(0, size * 0.25, size * 0.35, 1.2 * math.pi, 1.8 * math.pi, False).fill()

    @staticmethod
    def HEART(ctx):
        Image.text(ctx, "♥", x=0, y=0, font_size=180)

    @staticmethod
    def HEART_SMALL(ctx):
        Image.text(ctx, "♥", x=0, y=0, font_size=120)

    @staticmethod
    def YES(ctx):
        ctx.save()
        ctx.rgb(0, 1, 0)
        ctx.line_width = 18
        ctx.begin_path()
        ctx.move_to(-70, 0)
        ctx.line_to(-10, 40)
        ctx.line_to(70, -40)
        ctx.stroke()
        ctx.restore()

    @staticmethod
    def NO(ctx):
        ctx.save()
        ctx.rgb(1, 0, 0)
        ctx.line_width = 18
        ctx.begin_path()
        ctx.move_to(-60, -60)
        ctx.line_to(60, 60)
        ctx.move_to(-60, 60)
        ctx.line_to(60, -60)
        ctx.stroke()
        ctx.restore()

    @staticmethod
    def ARROW_N(ctx, size=140):
        ctx.save()
        Image._arrow(ctx, size)
        ctx.restore()


    @staticmethod
    def ARROW_S(ctx, size=140):
        ctx.save()
        ctx.rotate(math.pi)
        Image._arrow(ctx, size)
        ctx.restore()


    @staticmethod
    def ARROW_E(ctx, size=140):
        ctx.save()
        ctx.rotate(math.pi / 2)
        Image._arrow(ctx, size)
        ctx.restore()


    @staticmethod
    def ARROW_W(ctx, size=140):
        ctx.save()
        ctx.rotate(-math.pi / 2)
        Image._arrow(ctx, size)
        ctx.restore()

    @staticmethod
    def CONFUSED(ctx):
        Image._face_base(ctx, x=0, y=0, size=160)
        ctx.rgb(0, 0, 0)
        ctx.arc(-40, -20, 8, 0, 2 * math.pi, False).fill()
        ctx.arc(40, -20, 8, 0, 2 * math.pi, False).fill()
        ctx.line_width = 6
        ctx.begin_path()
        ctx.move_to(-30, 30)
        ctx.rel_line_to(15, -12)
        ctx.rel_line_to(15, 12)
        ctx.rel_line_to(15, -12)
        ctx.stroke()
        ctx.restore()

    @staticmethod
    def SURPRISED(ctx):
        Image._face_base(ctx, x=0, y=0, size=160)
        ctx.rgb(0, 0, 0)
        ctx.arc(-35, -20, 12, 0, 2 * math.pi, False).fill()
        ctx.arc(35, -20, 12, 0, 2 * math.pi, False).fill()
        ctx.arc(0, 30, 28, 0, 2 * math.pi, False).fill()
        ctx.restore()

    @staticmethod
    def ANGRY(ctx):
        Image._face_base(ctx, x=0, y=0, size=160)
        ctx.rgb(0, 0, 0)
        ctx.line_width = 12
        ctx.begin_path()
        ctx.move_to(-50, -50)
        ctx.line_to(-10, -30)
        ctx.stroke()
        ctx.begin_path()
        ctx.move_to(50, -50)
        ctx.line_to(10, -30)
        ctx.stroke()
        ctx.rgb(0, 0, 0)
        ctx.arc(0, 40, 56, 1.2 * math.pi, 1.8 * math.pi, False).fill()
        ctx.restore()


# auto-generate IMAGE_HANDLERS from uppercase Image methods
IMAGE_HANDLERS = {}
for _attr in dir(Image):
    if _attr.isupper():
        IMAGE_HANDLERS[_attr.lower()] = getattr(Image, _attr)

# Export a simple display instance
display = BadgeDisplay()
