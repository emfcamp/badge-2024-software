# BUGS: overrides what hexpansion driver has set to and
# doesn't restore them.

import asyncio
import time
from tildagonos import tildagonos

from machine import PWM

from app import App
from app_components import clear_background
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.hexpansion.config import HexpansionConfig
from system.eventbus import eventbus

from events.emote import EmotePositiveEvent, EmoteNegativeEvent

class EmoteBackLEDs(App):
  def __init__(self):
    eventbus.on_async(EmotePositiveEvent, self._positive_event, self)
    eventbus.on_async(EmoteNegativeEvent, self._negative_event, self)

  async def _positive_event(self, event):
    for lednum in range(13,19):
      tildagonos.leds[lednum] = (0,255,0)
    tildagonos.leds.write()
    await asyncio.sleep(0.5)
    for lednum in range(13,19):
      tildagonos.leds[lednum] = (0,0,0)
    tildagonos.leds.write()
 
  async def _negative_event(self, event):
    for lednum in range(13,19):
      tildagonos.leds[lednum] = (255,0,0)
    tildagonos.leds.write()
    await asyncio.sleep(0.5)
    for lednum in range(13,19):
      tildagonos.leds[lednum] = (0,0,0)
    tildagonos.leds.write()
