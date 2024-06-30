from _sim import _sim

EPIN_BTN_1 = (2, 6)
EPIN_BTN_2 = (2, 7)
EPIN_BTN_3 = (1, 0)
EPIN_BTN_4 = (1, 1)
EPIN_BTN_5 = (1, 2)
EPIN_BTN_6 = (1, 3)


class ePin:
    def __init__(self, pin):
        self.IN = 1
        self.OUT = 3
        self.PWM = 8
        self.pin = pin
    
    def init(self, mode):
        pass
    
    def on(self):
        pass
    
    def off(self):
        pass
    
    def duty(self, duty):
        pass
    
    def value(self, value=None):
        if value == None:
            if self.pin == EPIN_BTN_1:
                return not _sim.buttons.state()[0]
            elif self.pin == EPIN_BTN_2:
                return not _sim.buttons.state()[1]
            elif self.pin == EPIN_BTN_3:
                return not _sim.buttons.state()[2]
            elif self.pin == EPIN_BTN_4:
                return not _sim.buttons.state()[3]
            elif self.pin == EPIN_BTN_5:
                return not _sim.buttons.state()[4]
            elif self.pin == EPIN_BTN_6:
                return not _sim.buttons.state()[5]
            else:
                return 1
