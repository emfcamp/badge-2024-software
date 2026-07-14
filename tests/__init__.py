"""Test suite bootstrap.

These tests run under CPython, but the modules under test are written for
MicroPython. Importing this package wires up the things needed for that:

  * puts ``modules/`` on ``sys.path`` so the flat imports used by the firmware
    (``from async_queue import Queue`` etc.) resolve.
  * shims the MicroPython-only ``time.ticks_us`` / ``time.ticks_diff`` used by
    ``perf_timer`` and ``sys.print_exception`` used by the eventbus error
    handling so they import and run under CPython.
  * stubs the native ``display`` module
  * imports ``system.scheduler`` before anything imports.
    On the badge boot happens to import scheduler first, here we do it explicitly
    to prevent import issues.

Run from the project root with:  python -m unittest discover -t . -s tests
"""

import os
import sys
import time
import types

_MODULES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules"
)

if _MODULES not in sys.path:
    sys.path.insert(0, _MODULES)

if not hasattr(time, "ticks_us"):
    time.ticks_us = lambda: int(time.monotonic() * 1_000_000)
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b

if not hasattr(sys, "print_exception"):
    import traceback

    def _print_exception(exc, file=sys.stderr):
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=file)

    sys.print_exception = _print_exception

sys.modules.setdefault("display", types.ModuleType("display"))

import system.scheduler  # noqa: E402,F401