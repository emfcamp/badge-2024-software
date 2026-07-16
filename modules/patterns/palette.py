from patterns.base import BasePattern
from math import tanh
# from enum import Enum, auto

gamma8 = [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    2,
    3,
    3,
    3,
    3,
    3,
    3,
    3,
    4,
    4,
    4,
    4,
    4,
    5,
    5,
    5,
    5,
    6,
    6,
    6,
    6,
    7,
    7,
    7,
    7,
    8,
    8,
    8,
    9,
    9,
    9,
    10,
    10,
    10,
    11,
    11,
    11,
    12,
    12,
    13,
    13,
    13,
    14,
    14,
    15,
    15,
    16,
    16,
    17,
    17,
    18,
    18,
    19,
    19,
    20,
    20,
    21,
    21,
    22,
    22,
    23,
    24,
    24,
    25,
    25,
    26,
    27,
    27,
    28,
    29,
    29,
    30,
    31,
    32,
    32,
    33,
    34,
    35,
    35,
    36,
    37,
    38,
    39,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    50,
    51,
    52,
    54,
    55,
    56,
    57,
    58,
    59,
    60,
    61,
    62,
    63,
    64,
    66,
    67,
    68,
    69,
    70,
    72,
    73,
    74,
    75,
    77,
    78,
    79,
    81,
    82,
    83,
    85,
    86,
    87,
    89,
    90,
    92,
    93,
    95,
    96,
    98,
    99,
    101,
    102,
    104,
    105,
    107,
    109,
    110,
    112,
    114,
    115,
    117,
    119,
    120,
    122,
    124,
    126,
    127,
    129,
    131,
    133,
    135,
    137,
    138,
    140,
    142,
    144,
    146,
    148,
    150,
    152,
    154,
    156,
    158,
    160,
    162,
    164,
    167,
    169,
    171,
    173,
    175,
    177,
    180,
    182,
    184,
    186,
    189,
    191,
    193,
    196,
    198,
    200,
    203,
    205,
    208,
    210,
    213,
    215,
    218,
    220,
    223,
    225,
    228,
    231,
    233,
    236,
    239,
    241,
    244,
    247,
    249,
    252,
    255,
]


# A pattern based on showing a palette of colors around the badge and rotating it.
# a palette constructor arg should be supplied as follows:
#  * An array of 4 1-byte values (0-255): [index, r, g, b]
#  * The first color should be at index 0
# an interploation constructor arg can be provided as follows:
#  * 1 - None: change abruptly from one color to the next.
#  * 2 - Linear: change linearly from one color to the next. This is a smooth gradient but loses some definition of the palette colors themselves.
#  * 3 - Sigmoid: This smooths the transition between colors but emphasises the palette colors not the transition.
class PalettePattern(BasePattern):
    # class Interpolation(Enum):
    #    NONE = auto()
    #    LINEAR = auto()
    #    SIGMOID = auto()

    def __init__(
        self, num_leds=12, palette=None, num_frames=60, interpolation=2
    ):  # Interpolation.LINEAR):
        super().__init__()
        self._current_frame_id = 0
        self.fps = 30
        self.num_pixels = num_leds
        self.num_frames = num_frames
        self.interpolation = interpolation
        self.palette = self.validateAndNormalisePalette(palette)
        self.make_frames()

    def validateAndNormalisePalette(self, paletteIn):
        palette = paletteIn

        if palette is None:
            palette = [
                [0, 0, 0, 0],
                [128, 255, 255, 255],
            ]

        if palette[0][0] != 0:
            print(
                "first palette color should be at index 0 - using a default palette instead"
            )
            palette = [
                [0, 0, 0, 0],
                [128, 255, 255, 255],
            ]

        # Add an entry at 256 so we don't have to handle the wrapping in code.
        return palette + [[256, palette[0][1], palette[0][2], palette[0][3]]]

    def make_frames(self):
        self.frames = []
        for j in range(self.num_frames):
            current_row = []
            for i in range(self.num_pixels):
                rc_index = (
                    (i * 256 // self.num_pixels) + int(j * (255 / self.num_frames))
                ) & 255
                if rc_index < 0 or rc_index > 255:
                    current_row.append((0, 0, 0))
                else:
                    uncorrected_color = self.palette_pos(rc_index)
                    corrected_color = (
                        gamma8[int(uncorrected_color[0])],
                        gamma8[int(uncorrected_color[1])],
                        gamma8[int(uncorrected_color[2])],
                    )
                    current_row.append(corrected_color)
            self.frames.append(current_row)

    def palette_pos(self, i):
        prev_palette_entry = self.palette[-1]

        for palette_entry in self.palette:
            if palette_entry[0] == i:
                return (palette_entry[1], palette_entry[2], palette_entry[3])
            elif palette_entry[0] > i:
                # This is the palette_entry after the position we're looking for.
                palette_entry_weight = 0
                if self.interpolation == 2:  # Interpolation.LINEAR:
                    palette_entry_weight = (i - prev_palette_entry[0]) / (
                        palette_entry[0] - prev_palette_entry[0]
                    )
                elif self.interpolation == 3:  # Interpolation.SIGMOID:
                    x = i - prev_palette_entry[0]
                    a = palette_entry[0] - prev_palette_entry[0]

                    # normalise to [-1,1]
                    b = (x - (a / 2)) / (a / 2)
                    c = 3  # constant to make the sigmoid more or less agressive
                    palette_entry_weight = (tanh(b * c) + 1) / 2

                return (
                    palette_entry_weight * palette_entry[1]
                    + (1 - palette_entry_weight) * prev_palette_entry[1],
                    palette_entry_weight * palette_entry[2]
                    + (1 - palette_entry_weight) * prev_palette_entry[2],
                    palette_entry_weight * palette_entry[3]
                    + (1 - palette_entry_weight) * prev_palette_entry[3],
                )
            else:
                prev_palette_entry = palette_entry

        print("Couldn't interpolate palette position")
        return (0, 0, 0)
