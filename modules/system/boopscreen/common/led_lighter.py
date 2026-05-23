from tildagonos import tildagonos


class LEDLighter:
    """Light some LEDs."""

    def __init__(self, brightness):
        """Construct."""
        self.brightness = brightness

    def from_rgb(self, rgb):
        """Light lights from an RGB."""
        colour = rgb
        for i in range(12):
            tildagonos.leds[i + 1] = [int(i * self.brightness) for i in colour]

        tildagonos.leds.write()
