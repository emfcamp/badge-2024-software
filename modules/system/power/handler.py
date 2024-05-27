from system.eventbus import eventbus
from system.power import events

import power_event as pe


class PowerEventHandler:
    def RegisterDefaultCallbacks(self):
        pe.set_charge_cb(self.ChargeEventHandler)
        pe.set_device_attach_cb(self.DeviceAttachHandler)
        pe.set_device_detach_cb(self.DeviceDetachHandler)
        pe.set_fault_cb(self.FaultEventHandler)
        pe.set_host_attach_cb(self.HostAttachHandler)
        pe.set_host_detach_cb(self.HostDetachHandler)
        pe.set_lanyard_attach_cb(self.LanyardAttachHandler)
        pe.set_lanyard_detach_cb(self.LanyardDetachHandler)

    def ChargeEventHandler(self):
        eventbus.emit(
            events.RequestChargeEvent(events.PowerEvent("Charge Cycle change"))
        )

    def FaultEventHandler(self):
        eventbus.emit(events.RequestChargeFaultEvent(events.PowerEvent("Charge Fault")))

    def HostAttachHandler(self):
        eventbus.emit(
            events.RequestHostAttachEvent(events.PowerEvent("Host attatched"))
        )

    def HostDetachHandler(self):
        eventbus.emit(
            events.RequestHostDetachEvent(events.PowerEvent("Host Detatched"))
        )

    def DeviceAttachHandler(self):
        eventbus.emit(
            events.RequestDeviceAttachEvent(events.PowerEvent("Device attatched"))
        )

    def DeviceDetachHandler(self):
        eventbus.emit(
            events.RequestDeviceDetachEvent(events.PowerEvent("Device detatched"))
        )

    def LanyardAttachHandler(self):
        eventbus.emit(
            events.RequestLanyardAttachEvent(events.PowerEvent("Lanyard attatched"))
        )

    def LanyardDetachHandler(self):
        eventbus.emit(
            events.RequestLanyardDetachEvent(events.PowerEvent("Lanyard Detatched"))
        )
