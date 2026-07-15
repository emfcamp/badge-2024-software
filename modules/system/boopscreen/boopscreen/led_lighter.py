from tildagonos import tildagonos


class LEDLighter:
    """Light some LEDs."""

    def __init__(self, colour, brightness):
        """Construct."""
        self.colour = colour
        self.brightness = brightness

    def light(self):
        """Light lights from an RGB."""
        for i in range(12):
            tildagonos.leds[i + 1] = [int(i * self.brightness) for i in self.colour]

        tildagonos.leds.write()
