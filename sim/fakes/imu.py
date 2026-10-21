from typing import Tuple

import _sim

ACCEL_GYRO = 1
TEMPERATURE = 2
COMPASS = 3
STEPS = 4
OFF = 0

_periods = {
    ACCEL_GYRO: 40,
    TEMPERATURE: 1000,
    COMPASS: 40,
    STEPS: 1000,
}


def get_period(group):
    return _periods.get(group, 100)


def set_period(group, period_ms, force=False):
    if period_ms is None:
        _periods[group] = 100
        return True
    if period_ms < 10 or period_ms > 1000:
        raise ValueError("period must be between 10 and 1000 ms")
    _periods[group] = int(period_ms)
    return True


def acc_read() -> Tuple[float, float, float]:
    """
    Returns current x, y, z accelerations in m/s**2.
    """
    return (_sim._sim.acc[0], _sim._sim.acc[1], 3.0)


def gyro_read() -> Tuple[float, float, float]:
    """
    Returns current x, y, z rotation rate in degrees/s.
    """
    return (4.0, 5.0, 6.0)


def mag_read() -> Tuple[float, float, float]:
    """
    Returns current x, y, z magnetic field values.
    """
    return (1.0, 2.0, 3.0)


def temperature_read() -> float:
    return 23.4


def step_counter_read() -> int:
    return 1337
