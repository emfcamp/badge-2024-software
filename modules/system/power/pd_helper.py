from pd import Host, Device


class vdmCmd:
    DISCOVER_IDENTITY = 1
    DISCOVER_SVIDS = 2
    DISCOVER_MODES = 3
    ENTER_MODE = 4
    EXIT_MODE = 5
    ATTENTION = 6


class dataType:
    SOURCE_CAPABILITIES = 1
    REQUEST = 2
    BIST = 3
    SINK_CAPABILITIES = 4
    BATTERY_STATUS = 5
    ALERT = 6
    GET_COUNTRY_INFO = 7
    ENTER_USB = 8
    EPR_REQUEST = 9
    EPR_MODE = 10
    SOURCE_INFO = 11
    REVISION = 12
    VENDOR_DEFINED = 15


class cmdType:
    ACCEPT = 3
    REJECT = 4
    SOFT_RESET = 13
    NOT_SUPPORTED = 16
    GET_STATUS = 18


class pdHelper:
    def pd_header(self, message_type, no_objects=0, extended=0):
        # the majority of the header is filled in by the badge
        header = (extended << 15) | (no_objects << 12) | message_type
        return header

    def vdm_structured_header(
        self, command, SVID=0xFF00, cmd_type=0, obj_pos=0, vdm_minor=0, vdm_major=0
    ):
        vdmh = (
            (SVID << 16)
            | (1 << 15)
            | (vdm_major << 13)
            | (vdm_minor << 11)
            | (obj_pos << 8)
            | (cmd_type << 6)
            | command
        )
        return vdmh

    def vdm_unstructured_header(self, SVID=0xFF00, data=0):
        vdmh = (SVID << 16) | (0x7FFF & data)
        return vdmh

    # def host_disc_id_prime(self):
    #    header = self.pd_header(dataType.VENDOR_DEFINED, 1)
    #    data = self.vdm_structured_header(vdmCmd.DISCOVER_IDENTITY)
    #    pd.send_host_prime_msg(header, data.to_bytes(4, 'little'), 4)

    # def host_disc_id_dbl_prime(self):
    #    header = self.pd_header(dataType.VENDOR_DEFINED, 1)
    #    data = self.vdm_structured_header(vdmCmd.DISCOVER_IDENTITY)
    #    pd.send_host_dbl_prime_msg(header, data.to_bytes(4, 'little'), 4)

    def host_send_badge_id(self):
        tildagon_message = bytearray(
            [
                0x00,
                0x00,
                0x00,
                0xFF,
                0x54,
                0x69,
                0x6C,
                0x64,
                0x61,
                0x67,
                0x6F,
                0x6E,
                0x42,
                0x65,
                0x73,
                0x74,
                0x61,
                0x67,
                0x6F,
                0x6E,
            ]
        )
        usb_out = Host()
        usb_out.send_vendor_msg(tildagon_message, 5)

    def device_send_badge_id(self):
        tildagon_message = bytearray(
            [
                0x00,
                0x00,
                0x00,
                0xFF,
                0x54,
                0x69,
                0x6C,
                0x64,
                0x61,
                0x67,
                0x6F,
                0x6E,
                0x42,
                0x65,
                0x73,
                0x74,
                0x61,
                0x67,
                0x6F,
                0x6E,
            ]
        )
        usb_in = Device()
        usb_in.send_vendor_msg(tildagon_message, 5)
