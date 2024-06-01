import json

_PATH = "/settings.json"
_settings = None
_modified = False


def load():
    global _settings, _modified
    try:
        with open(_PATH, "r") as f:
            _settings = json.load(f)
    except Exception:
        _settings = {}
    _modified = False


def get(k, default=None):
    if _settings is None:
        load()
    return _settings.get(k, default)


def set(k, v):
    global _modified
    if _settings is None:
        load()
    if v is None:
        del _settings[k]
    else:
        _settings[k] = v
    _modified = True


def save():
    global _settings, _modified
    if _settings is None:
        load()
    if _modified:
        with open(_PATH, "w") as f:
            json.dump(_settings, f)
        _modified = False
