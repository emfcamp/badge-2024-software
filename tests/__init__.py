"""Test suite bootstrap.

These tests run under CPython, but the modules under test are written for
MicroPython. Importing this package wires up the two things needed for that:

  * puts ``modules/`` on ``sys.path`` so the flat imports used by the firmware
    (``from async_queue import Queue`` etc.) resolve; and
  * shims the MicroPython-only ``time.ticks_us`` / ``time.ticks_diff`` used by
    ``perf_timer`` so it imports and runs under CPython.

Run from the project root with:  python -m unittest discover -t . -s tests
"""

import os
import sys
import time

_MODULES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules"
)

if _MODULES not in sys.path:
    sys.path.insert(0, _MODULES)

if not hasattr(time, "ticks_us"):
    time.ticks_us = lambda: int(time.monotonic() * 1_000_000)
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b