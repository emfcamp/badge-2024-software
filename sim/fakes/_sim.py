import ctx
import math
import os
import time
import itertools
import sys

import pygame

try:
    import config as CONFIG
except ImportError:
    print("Info: No custom config.py found")

pygame.init()
screen_w = 733
screen_h = 733
screen = pygame.display.set_mode(size=(screen_w, screen_h))
simpath = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
bgpath = os.path.join(simpath, "background.png")
background = pygame.image.load(bgpath)


SCREENSHOT = False
SCREENSHOT_DELAY = 5


def path_replace(p):
    simpath = "/tmp/flow3r-sim"
    projectpath = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    )
    if p.startswith("/flash/sys"):
        p = p[len("/flash/sys") :]
        p = projectpath + "/modules" + p
        return p
    if p.startswith("/flash"):
        p = p[len("/flash") :]
        p = simpath + p
        return p

    return p


class Input:
    """
    Input implements an input overlay (for petals or buttons) that can be
    mouse-picked by the user, and in the future also keyboard-controlled.
    """

    # Pixels positions of each marker.
    POSITIONS = []
    # Keyboard mapping
    KEYS = []
    # Pixel size (diameter) of each marker.
    MARKER_SIZE = 150

    # Colors for various states (RGBA).
    COLOR_HELD = (0x5B, 0x1B, 0x1B, 0xA0)
    COLOR_HOVER = (0x6B, 0x1B, 0x1B, 0xA0)
    COLOR_IDLE = (0xFB, 0xFB, 0xFB, 0x80)

    def __init__(self):
        self._state = [False for _ in self.POSITIONS]
        self._mouse_hover = None
        self._mouse_held = None

    def state(self):
        s = [ss for ss in self._state]
        if self._mouse_held is not None:
            s[self._mouse_held] = True
        return s

    def _mouse_coords_to_id(self, mouse_x, mouse_y):
        for i, (x, y) in enumerate(self.POSITIONS):
            dx = mouse_x - x
            dy = mouse_y - y
            if math.sqrt(dx**2 + dy**2) < self.MARKER_SIZE // 2:
                return i
        return None

    def process_event(self, ev):
        prev_hover = self._mouse_hover
        prev_state = self.state()

        if ev.type == pygame.MOUSEMOTION:
            x, y = ev.pos
            self._mouse_hover = self._mouse_coords_to_id(x, y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_held = self._mouse_hover
        if ev.type == pygame.MOUSEBUTTONUP:
            self._mouse_held = None
        if ev.type in [pygame.KEYDOWN, pygame.KEYUP]:
            if ev.key in self.KEYS:
                self._mouse_hover = self.KEYS.index(ev.key)
            if ev.type == pygame.KEYDOWN:
                self._mouse_held = self._mouse_hover
            if ev.type == pygame.KEYUP:
                self._mouse_held = None
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if ev.type == pygame.USEREVENT:
            _sim.render_gui_lazy()

        if prev_hover != self._mouse_hover:
            return True
        if prev_state != self.state():
            return True
        return False

    def render(self, surface):
        s = self.state()
        for i, (x, y) in enumerate(self.POSITIONS):
            if s[i]:
                pygame.draw.circle(
                    surface, self.COLOR_HELD, (x, y), self.MARKER_SIZE // 2
                )
            elif i == self._mouse_hover:
                pygame.draw.circle(
                    surface, self.COLOR_HOVER, (x, y), self.MARKER_SIZE // 2
                )
            else:
                pygame.draw.circle(
                    surface, self.COLOR_IDLE, (x, y), self.MARKER_SIZE // 2
                )


class ButtonsInput(Input):
    POSITIONS = [
        (370, 33),
        (670, 190),
        (670, 540),
        (370, 710),
        (75, 540),
        (85, 190),
    ]

    # Default keyboard mapping
    button_map = {
        "left_jog_left": pygame.K_a,
        "left_press": pygame.K_b,
        "left_jog_right": pygame.K_c,
        "right_jog_left": pygame.K_d,
        "right_press": pygame.K_e,
        "right_jog_right": pygame.K_f,
    }

    # Load custom keymapping if available
    try:
        if CONFIG.button_map != {}:
            button_map = CONFIG.button_map
    except:
        print("Info: No custom button mapping found in config.py")

    KEYS = [
        button_map["left_jog_left"],
        button_map["left_press"],
        button_map["left_jog_right"],
        button_map["right_jog_left"],
        button_map["right_press"],
        button_map["right_jog_right"],
    ]

    MARKER_SIZE = 50
    COLOR_HELD = (0xF0, 0x00, 0x00, 0xFF)
    COLOR_HOVER = (0xF0, 0x00, 0x00, 0x5F)
    COLOR_IDLE = (0xC0, 0xC0, 0xC0, 0x5F)


class GravityInput(Input):
    POSITIONS = [
        (56, 120 - 32),
        (24, 120),
        (56, 120 + 32),
        (88, 120),
    ]
    KEYS = [
        pygame.K_w,
        pygame.K_a,
        pygame.K_s,
        pygame.K_d,
    ]
    ACC = [
        (-1, 0),
        (0, -1),
        (1, 0),
        (0, 1),
    ]
    MARKER_SIZE = 40
    COLOR_HELD = (0x80, 0x80, 0x80, 0xFF)
    COLOR_HOVER = (0x40, 0x40, 0x40, 0xFF)
    COLOR_IDLE = (0x20, 0x20, 0x20, 0xFF)
    TILT_POS = [56, 120]
    TILT_SIZE = 10
    TILT_COLOR = (0x40, 0x40, 0xFF, 0xFF)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.acc = (0, 0)
        self._old_pos = self.TILT_POS

    def process_event(self, ev):
        """Each WASD key press adds a bit of acceleration in the given direction."""
        res = super().process_event(ev)
        # self.acc = (0, 0)
        if not res:
            return res
        if self._mouse_held is not None:
            self.acc = self.ACC[self._mouse_held]

        return True

    def render(self, surface, acc):
        pygame.draw.circle(surface, (0, 0, 0, 0xFF), self._old_pos, self.TILT_SIZE)
        super().render(surface)
        self._old_pos = (self.TILT_POS[0] + acc[1] * 2, self.TILT_POS[1] + acc[0] * 2)
        pygame.draw.circle(surface, self.TILT_COLOR, self._old_pos, self.TILT_SIZE // 2)


class Simulation:
    """
    Simulation implements the state and logic of the on-host pygame-based badge
    simulator.
    """

    # Pixel coordinates of each LED. The order is the same as the hardware
    # WS2812 chain, not the order as expected by the micropython API!
    LED_POSITIONS = [
        # Internal
        (370, 370),
        
        # Top
        (443, 90),
        (573, 163),
        (646, 293),
        (646, 440),
        (573, 566),
        (443, 640),
        
        (296, 640),
        (173, 566),
        (93, 440),
        (93, 293),
        (173, 163),
        (296, 90),

        # Under
        (533, 93),
        (680, 366),
        (533, 626),
        (200, 626),
        (60, 366),
        (200, 93),
    ]

    def __init__(self):
        # Buffered LED state. Will be propagated to led_state when the
        # simulated update_leds function gets called.
        self.led_state_buf = [(0, 0, 0) for _ in self.LED_POSITIONS]
        # Actual LED state as rendered.
        self.led_state = [(0, 0, 0) for _ in self.LED_POSITIONS]
        self.buttons = ButtonsInput()
        self.grav = GravityInput()
        self.acc = [0, 0]
        # Timestamp of last GUI render. Used by the lazy render GUI
        # functionality.
        self.last_gui_render = None

        # Surfaces for different parts of the simulator render. Some of them
        # have a dirty bit which is an optimization to skip rendering the
        # corresponding surface when there was no change to its render data.
        self._led_surface = pygame.Surface((screen_w, screen_h), flags=pygame.SRCALPHA)
        self._led_surface_dirty = True
        self._button_surface = pygame.Surface(
            (screen_w, screen_h), flags=pygame.SRCALPHA
        )
        self._button_surface_dirty = True
        self._full_surface = pygame.Surface((screen_w, screen_h), flags=pygame.SRCALPHA)
        self._oled_surface = pygame.Surface((240, 240), flags=pygame.SRCALPHA)

        # Calculate OLED per-row offset.
        #
        # The OLED disc (240px diameter) will be written into a 240px x 240px
        # axis-aligned bounding box. The rendering routine iterates over the
        # bounding box row-per-row, and we only want to write that row's disc
        # fragment for each row into the square bounding box. This fragment
        # will be offset by some pixels from the left edge, and will be also
        # shortened by the same count of pixels from the right edge.
        #
        # The way we calculate these offsets is quite naïve, but it's easy to
        # reason about. First, we start off by calculating a 240x240px bitmask
        # that is True if the pixel corresponding to this mask's bit is part of
        # the OLED disc, and false otherwise.
        mask = [
            [math.sqrt((x - 120) ** 2 + (y - 120) ** 2) <= 120 for x in range(240)]
            for y in range(240)
        ]
        # Now, we iterate the mask row-by-row and find the first True bit in
        # it. The offset within that row is our per-row offset for the
        # rendering routine.
        self._oled_offset = [m.index(True) for m in mask]

    def process_events(self):
        """
        Process pygame events and update mouse_{x,y}, {petal,button}_held and
        {petal,button}_hover.
        """
        evs = pygame.event.get()
        for ev in evs:
            if self.buttons.process_event(ev):
                self._button_surface_dirty = True
            if self.grav.process_event(ev):
                self._button_surface_dirty = True
                self.acc[0] += self.grav.acc[0]
                self.acc[1] += self.grav.acc[1]

    def _render_button_markers(self, surface):
        self.buttons.render(surface)
        # self.grav.render(surface, self.acc)

    def _render_leds(self, surface, top=True, bottom=True):
        for pos, state, n in zip(
            self.LED_POSITIONS, self.led_state, range(len(self.LED_POSITIONS))
        ):
            # TODO(q3k): pre-apply to LED_POSITIONS
            x = pos[0] + 3.0
            y = pos[1] + 3.0
            r, g, b = state
            if 13 <= n and bottom:
                # This is the top board, big diffuse circle
                for i in range(20):
                    radius = 100 - i
                    r2 = r / (100 - i * 5)
                    g2 = g / (100 - i * 5)
                    b2 = b / (100 - i * 5)
                    pygame.draw.circle(surface, (r2, g2, b2), (x, y), radius)
            if 1 <= n < 13 and top:
                for i in range(20):
                    radius = 26 - i
                    pygame.draw.circle(
                        surface, (r, g, b, 250 - ((20 - i) * 10)), (x, y), radius
                    )

    def _render_oled(self, surface, fb):
        surface.fill((0, 0, 0, 0))
        buf = surface.get_buffer()

        fb = fb[: 240 * 240 * 4]
        for y in range(240):
            # Use precalculated row offset to turn OLED disc into square
            # bounded plane.
            offset = self._oled_offset[y]
            start_offs_bytes = y * 240 * 4
            start_offs_bytes += offset * 4
            end_offs_bytes = (y + 1) * 240 * 4
            end_offs_bytes -= offset * 4
            buf.write(bytes(fb[start_offs_bytes:end_offs_bytes]), start_offs_bytes)

    def render_gui_now(self):
        """
        Render the GUI elements, skipping overlay elements that aren't dirty.

        This does _not_ render the Ctx state into the OLED surface. For that,
        call render_display.
        """
        self.last_gui_render = time.time()

        full = self._full_surface
        if self._led_surface_dirty or self._button_surface_dirty:
            full.fill((0, 0, 0, 255))
            self._render_leds(full, bottom=True, top=False)
            full.blit(background, (0, 0))

            self._led_surface.fill((255, 255, 255, 0))
            self._render_leds(self._led_surface, bottom=False, top=True)
            self._led_surface_dirty = False
            full.blit(self._led_surface, (0, 0))

            self._render_button_markers(self._button_surface)
            self._button_surface_dirty = False
            full.blit(self._button_surface, (0, 0))

        # Always blit oled. Its' alpha blending is designed in a way that it
        # can be repeatedly applied to a dirty _full_surface without artifacts.
        center_x = 370
        center_y = 366
        off_x = center_x - (240 // 2)
        off_y = center_y - (240 // 2)
        full.blit(self._oled_surface, (off_x, off_y))

        screen.blit(full, (0, 0))
        pygame.display.flip()

    def render_gui_lazy(self):
        """
        Render the GUI elements if needed to maintain a responsive 60fps of the
        GUI itself. As with render_gui_now, the OLED surface is not rendered by
        this call.
        """
        target_fps = 60.0
        d = 1 / target_fps

        if self.last_gui_render is None:
            self.render_gui_now()
        elif time.time() - self.last_gui_render > d:
            self.render_gui_now()

    def render_display(self, fb):
        """
        Render the OLED surface from Ctx state.

        Afterwards, render_gui_{lazy,now} should still be called to actually
        present the new OLED surface state to the user.
        """
        self._render_oled(self._oled_surface, fb)

    def set_led_rgb(self, ix, r, g, b):
        self.led_state_buf[ix] = (r * 255, g * 255, b * 255)

    def leds_update(self):
        for i, s in enumerate(_sim.led_state_buf):
            if _sim.led_state[i] != s:
                _sim.led_state[i] = s
                self._led_surface_dirty = True


_sim = Simulation()


class FramebufferManager:
    def __init__(self):
        self._free = []

        # Significant difference between on-device Ctx and simulation Ctx: we
        # render to a BRGA8 (24bpp color + 8bpp alpha) buffer instead of 16bpp
        # RGB565 like the device does. This allows us to directly blit the ctx
        # framebuffer into pygame's surfaces, which is a _huge_ speed benefit
        # (difference between ~10FPS and 500+FPS!).

        for _ in range(1):
            fb, c = ctx._wasm.ctx_new_for_framebuffer(240, 240, 240 * 4, ctx.RGBA8)
            ctx._wasm.ctx_apply_transform(c, 1, 0, 120, 0, 1, 120, 0, 0, 1)
            self._free.append((fb, c))

        self._overlay = ctx._wasm.ctx_new_for_framebuffer(240, 240, 240 * 4, ctx.RGBA8)
        ctx._wasm.ctx_apply_transform(self._overlay[1], 1, 0, 120, 0, 1, 120, 0, 0, 1)

        self._output = ctx._wasm.ctx_new_for_framebuffer(240, 240, 240 * 4, ctx.BGRA8)

    def get(self):
        if len(self._free) == 0:
            return None, None
        fb, ctx = self._free[0]
        self._free = self._free[1:]

        return fb, ctx

    def put(self, fb, ctx):
        self._free.append((fb, ctx))

    def get_overlay(self):
        return self._overlay

    def get_output(self, fbp):
        return self._output

    def draw(self, fb):
        ctx._wasm.ctx_define_texture(
            self._output[1], "!fb", 240, 240, 240 * 4, ctx.RGBA8, fb, 0
        )
        ctx._wasm.ctx_parse(self._output[1], "compositingMode copy")
        ctx._wasm.ctx_draw_texture(self._output[1], "!fb", 0, 0, 240, 240)

        if overlay_clip[2] and overlay_clip[3]:
            ctx._wasm.ctx_define_texture(
                self._output[1],
                "!overlay",
                240,
                240,
                240 * 4,
                ctx.RGBA8,
                self._overlay[0],
                0,
            )
            ctx._wasm.ctx_parse(self._output[1], "compositingMode sourceOver")
            ctx._wasm.ctx_draw_texture(self._output[1], "!overlay", 0, 0, 240, 240)


fbm = FramebufferManager()
overlay_ctxs = []
overlay_clip = (0, 0, 240, 240)


def set_overlay_clip(x, y, x2, y2):
    global overlay_clip
    overlay_clip = (x, y, x2 - x, y2 - y)


def start_frame():
    dctx = ctx._wasm.ctx_new_drawlist(240, 240)
    return ctx.Context(dctx)


def get_overlay_ctx():
    dctx = ctx._wasm.ctx_new_drawlist(240, 240)
    overlay_ctxs.append(dctx)
    return ctx.Context(dctx)


def display_update(subctx):
    _sim.process_events()

    if subctx._ctx in overlay_ctxs:
        overlay_ctxs.remove(subctx._ctx)
        fbp, c = fbm.get_overlay()
        ctx._wasm.ctx_render_ctx(subctx._ctx, c)
        ctx._wasm.ctx_destroy(subctx._ctx)
        return

    fbp, c = fbm.get()

    if fbp is None:
        return

    ctx._wasm.ctx_render_ctx(subctx._ctx, c)
    ctx._wasm.ctx_destroy(subctx._ctx)

    fbm.draw(fbp)

    fb = ctx._wasm._i.exports.memory.uint8_view(fbm.get_output(fbp)[0])

    _sim.render_display(fb)
    _sim.render_gui_now()

    global SCREENSHOT
    global SCREENSHOT_DELAY
    if SCREENSHOT:
        SCREENSHOT_DELAY -= 1
        if SCREENSHOT_DELAY <= 0:
            path = os.curdir + "/flow3r.png"
            pygame.image.save(screen, path)
            print("Saved screenshot to ", path)
            sys.exit(0)

    fbm.put(fbp, c)


def get_button_state(left):
    _sim.process_events()
    _sim.render_gui_lazy()

    state = _sim.buttons.state()
    if left == 1:
        sub = state[:3]
    elif left == 0:
        sub = state[3:6]
    else:
        return 0

    if sub[0]:
        return -1
    elif sub[1]:
        return 2
    elif sub[2]:
        return +1
    return 0
