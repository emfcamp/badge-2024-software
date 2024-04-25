_volume = 0
_muted = False

INPUT_SOURCE_NONE = None
INPUT_SOURCE_AUTO = None
INPUT_SOURCE_HEADSET_MIC = None
INPUT_SOURCE_LINE_IN = None
INPUT_SOURCE_ONBOARD_MIC = None


def set_volume_dB(v: float) -> None:
    global _volume
    _volume = v


def get_volume_dB() -> float:
    global _volume
    return _volume


def get_volume_relative() -> float:
    return (_volume + 47) / (47 + 14)


def headphones_set_volume_dB(v: float) -> None:
    pass


def speaker_set_volume_dB(v: float) -> None:
    pass


def headphones_set_minimum_volume_dB(v: float) -> None:
    pass


def speaker_set_minimum_volume_dB(v: float) -> None:
    pass


def headphones_set_maximum_volume_dB(v: float) -> None:
    pass


def speaker_set_maximum_volume_dB(v: float) -> None:
    pass


def speaker_set_eq_on(enable: bool) -> None:
    pass


def adjust_volume_dB(v) -> float:
    global _volume
    _volume += v
    if _volume < -48:
        _volume = -47
    if _volume > 14:
        _volume = 14


def headphones_are_connected() -> bool:
    return False


def line_in_is_connected() -> bool:
    return False


def set_mute(v: bool) -> None:
    global _muted
    _muted = v


def get_mute() -> bool:
    global _muted
    return _muted


def headset_mic_set_gain_dB(v: float) -> None:
    pass


def headset_mic_get_gain_dB() -> float:
    return 10


def onboard_mic_set_gain_dB(v: float) -> None:
    pass


def onboard_mic_get_gain_dB() -> float:
    return 10


def line_in_set_gain_dB(v: float) -> None:
    pass


def line_in_get_gain_dB() -> float:
    return 10


def headset_mic_set_allowed(v: bool) -> None:
    pass


def onboard_mic_set_allowed(v: bool) -> None:
    pass


def line_in_set_allowed(v: bool) -> None:
    pass


def onboard_mic_to_speaker_set_allowed(v: bool) -> None:
    pass


def headget_mic_get_allowed() -> bool:
    return True


def onboard_mic_get_allowed() -> bool:
    return True


def line_in_get_allowed() -> bool:
    return True


def onboard_mic_to_speaker_get_allowed() -> bool:
    return False


def input_thru_set_source(source):
    pass


def input_thru_get_source():
    return None


def input_engines_get_source_avail(source):
    return False


def headset_mic_get_allowed():
    return False


def input_engines_get_source():
    return None


def input_thru_get_mute():
    return False


def input_thru_set_mute(mute):
    pass


def input_engines_set_source(source):
    pass
