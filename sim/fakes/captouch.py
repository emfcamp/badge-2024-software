from typing import List


class CaptouchPetalPadsState:
    def __init__(self, tip, base, cw, ccw) -> None:
        self._tip = tip
        self._base = base
        self._cw = cw
        self._ccw = ccw

    @property
    def tip(self) -> bool:
        return self._tip

    @property
    def base(self) -> bool:
        return self._base

    @property
    def cw(self) -> bool:
        return self._cw

    @property
    def ccw(self) -> bool:
        return self._ccw


class CaptouchPetalState:
    def __init__(self, ix: int, pads: CaptouchPetalPadsState):
        self._pads = pads
        self._ix = ix
        self.position = (0, 0)

    @property
    def pressure(self) -> int:
        if not self.pressed:
            return 0
        return 1000

    @property
    def pressed(self) -> bool:
        if self.top:
            return self._pads.base or self._pads.ccw or self._pads.cw
        else:
            return self._pads.tip or self._pads.base

    @property
    def top(self) -> bool:
        return self._ix % 2 == 0

    @property
    def bottom(self) -> bool:
        return not self.top

    @property
    def pads(self) -> CaptouchPetalPadsState:
        return self._pads


class CaptouchState:
    def __init__(self, petals: List[CaptouchPetalState]):
        self._petals = petals

    @property
    def petals(self) -> List[CaptouchPetalState]:
        return self._petals


def read() -> CaptouchState:
    import _sim

    _sim._sim.process_events()
    _sim._sim.render_gui_lazy()
    petals = _sim._sim.petals

    res = []
    for petal in range(10):
        top = petal % 2 == 0
        if top:
            ccw = petals.state_for_petal_pad(petal, 1)
            cw = petals.state_for_petal_pad(petal, 2)
            base = petals.state_for_petal_pad(petal, 3)
            pads = CaptouchPetalPadsState(False, base, cw, ccw)
            res.append(CaptouchPetalState(petal, pads))
        else:
            tip = petals.state_for_petal_pad(petal, 0)
            base = petals.state_for_petal_pad(petal, 3)
            pads = CaptouchPetalPadsState(tip, base, False, False)
            res.append(CaptouchPetalState(petal, pads))
    return CaptouchState(res)


def calibration_active() -> bool:
    return False


def calibration_request() -> None:
    return


def refresh_events() -> None:
    return
