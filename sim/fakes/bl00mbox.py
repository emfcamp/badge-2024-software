import pygame
from _sim import path_replace


class _mock(list):
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        if attr in ["tone", "value", "dB", "SQUARE", "SAW"]:
            return 0
        if attr in ["trigger_state"]:
            return lambda *args: 0
        if attr in ["_Patch"]:
            return _mock
        return _mock()

    def __getitem__(self, item):
        return _mock()

    def __setitem__(self, item, val):
        pass

    def __call__(self, *args, **kwargs):
        return _mock()


class Channel:
    def __init__(self, id):
        pass

    def new(self, a, *args, **kwargs):
        return a(self, *args, **kwargs)

    def clear(self):
        pass

    mixer = None
    channel_num = 0
    volume = 8000


class _patches(_mock):
    class sampler(_mock):
        class Signals(_mock):
            class Trigger(_mock):
                def __init__(self, sampler):
                    self._sampler = sampler

                def start(self):
                    self._sampler._sound.set_volume(
                        self._sampler._channel.volume / 32767
                    )
                    self._sampler._sound.play()

            def __init__(self, sampler):
                self._sampler = sampler
                self._trigger = patches.sampler.Signals.Trigger(sampler)

            @property
            def trigger(self):
                return self._trigger

            @trigger.setter
            def trigger(self, val):
                pass

        def _convert_filename(self, filename):
            if filename.startswith("/flash/") or filename.startswith("/sd/"):
                return filename
            elif filename.startswith("/"):
                return "/flash/" + filename
            else:
                return "/flash/sys/samples/" + filename

        def __init__(self, channel, path):
            if type(path) == int:
                self._signals = _mock()
                return
            self._sound = pygame.mixer.Sound(path_replace(self._convert_filename(path)))
            self._signals = patches.sampler.Signals(self)
            self._channel = channel

        @property
        def signals(self):
            return self._signals


class _helpers(_mock):
    def sct_to_note_name(self, sct):
        sct = sct - 18367 + 100
        octave = ((sct + 9 * 200) // 2400) + 4
        tones = ["A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab"]
        tone = tones[(sct // 200) % 12]
        return tone + str(octave)

    def note_name_to_sct(self, name):
        tones = ["A", "Bb", "B", "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab"]
        semitones = tones.index(name[0])
        if semitones > 2:
            semitones -= 12
        if name[1] == "b":
            octave = int(name[2:])
            semitones -= 1
        elif name[1] == "#":
            octave = int(name[2:])
            semitones += 1
        else:
            octave = int(name[1:])
        return 18367 + (octave - 4) * 2400 + (200 * semitones)

    def sct_to_freq(sct):
        return 440 * 2 ** ((sct - 18367) / 2400)


plugins = _mock()
patches = _patches()
helpers = _helpers()
