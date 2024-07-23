from app import App
import power
import asyncio


class PowerManager(App):
    def __init__(self): ...

    async def background_task(self):
        while True:
            if power.Vbat() < 3.5 and power.Vin() < 4.5:
                power.Off()
            await asyncio.sleep(10)


__app_export__ = PowerManager
