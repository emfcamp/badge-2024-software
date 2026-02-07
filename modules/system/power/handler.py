from system.eventbus import eventbus
from system.power import events
from system.power.pd_helper import pdHelper
from system.notification.events import ShowNotificationEvent
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
        pe.set_badge_as_device_attach_cb(self.BadgeAsDeviceAttachHandler)
        pe.set_badge_as_device_detach_cb(self.BadgeAsDeviceDetachHandler)
        pe.set_badge_as_host_attach_cb(self.BadgeAsHostAttachHandler)
        pe.set_badge_as_host_detach_cb(self.BadgeAsHostDetachHandler)
        pe.set_device_vendor_msg_rx_cb(self.VendorMsgDevRxHandler)
        pe.set_host_vendor_msg_rx_cb(self.VendorMsgHostRxHandler)
        pe.set_host_prime_msg_rx_cb(self.PrimeMsgHostRxHandler)
        pe.set_host_dbl_prime_msg_rx_cb(self.DoublePrimeMsgHostRxHandler)

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

    def BadgeAsDeviceAttachHandler(self):
        eventbus.emit(ShowNotificationEvent("Badge Connected as Device"))
        eventbus.emit(events.BadgeAsDeviceAttachEvent())
        pdh = pdHelper()
        pdh.device_send_badge_id()

    def BadgeAsDeviceDetachHandler(self):
        eventbus.emit(ShowNotificationEvent("Badge Device disconnected"))
        eventbus.emit(events.BadgeAsDeviceDetachEvent())

    def BadgeAsHostAttachHandler(self):
        eventbus.emit(ShowNotificationEvent("Badge Connected as Host"))
        eventbus.emit(events.BadgeAsHostAttachEvent())

    def BadgeAsHostDetachHandler(self):
        eventbus.emit(ShowNotificationEvent("Badge Host disconnected"))
        eventbus.emit(events.BadgeAsHostDetachEvent())

    def VendorMsgDevRxHandler(self):
        eventbus.emit(events.VendorMsgDevRxEvent())

    def VendorMsgHostRxHandler(self):
        eventbus.emit(events.VendorMsgHostRxEvent())

    def PrimeMsgHostRxHandler(self):
        eventbus.emit(events.PrimeMsgHostRxEvent())

    def DoublePrimeMsgHostRxHandler(self):
        eventbus.emit(events.DblPrimeMsgHostRxEvent())
