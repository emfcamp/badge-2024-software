from app import App
import power
import asyncio
from micropython import const


_LOW_BATTERY_MILLIVOLTS = const(3500)
_LOW_INPUT_MILLIVOLTS = const(4500)


class PowerManager(App):
    def __init__(self): ...

    async def background_task(self):
        while True:
            if (
                power.VbatMilliVolts() < _LOW_BATTERY_MILLIVOLTS
                and power.VinMilliVolts() < _LOW_INPUT_MILLIVOLTS
            ):
                power.Off()
            await asyncio.sleep(10)


__app_export__ = PowerManager
