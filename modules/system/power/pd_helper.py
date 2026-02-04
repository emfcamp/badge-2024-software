from pd import Host, Device


class vdmCmd:
    DISCOVER_IDENTITY = 1
    DISCOVER_SVIDS = 2
    DISCOVER_MODES = 3
    ENTER_MODE = 4
    EXIT_MODE = 5
    ATTENTION = 6


class dataType:
    BIST = 3
    VENDOR_DEFINED = 15


class cmdType:
    ACCEPT = 3
    REJECT = 4
    SOFT_RESET = 13


class pdHelper:
    def pd_header(self, message_type, no_objects=0):
        # the majority of the header is filled in by the badge
        header = (no_objects << 12) | message_type
        return header

    def vdm_structured_header(self, command, SVID=0xFF00, obj_pos=0, Version=0):
        vdmh = (SVID << 16) | (1 << 15) | (Version << 13) | (obj_pos << 8) | command
        return vdmh

    def vdm_unstructured_header(self, SVID=0xFF00, data=0):
        vdmh = (SVID << 16) | (0x7FFF & data)
        return vdmh

    def vdm_header_extract(self, vendor_header):
        header = {
            "SVID": vendor_header >> 16,
            "structured": (vendor_header >> 15) & 0x01,
            "data": None,
            "Version": None,
            "obj_pos": None,
            "cmd_type": None,
            "cmd": None,
        }
        if header["structured"] == 1:
            header["Version"] = (vendor_header >> 13) & 0x03
            header["obj_pos"] = (vendor_header >> 8) & 0x07
            header["cmd_type"] = (vendor_header >> 6) & 0x03
            header["cmd"] = vendor_header & 0x3F
        else:
            header["data"] = vendor_header & 0x7FFF
        return header

    def host_disc_id_prime(self):
        header = self.pd_header(dataType.VENDOR_DEFINED, 1)
        data = self.vdm_structured_header(vdmCmd.DISCOVER_IDENTITY)
        usb_out = Host()
        usb_out.send_prime_msg(
            header.to_bytes(2, "little") + data.to_bytes(4, "little")
        )

    def host_disc_id_dbl_prime(self):
        header = self.pd_header(dataType.VENDOR_DEFINED, 1)
        data = self.vdm_structured_header(vdmCmd.DISCOVER_IDENTITY)
        usb_out = Host()
        usb_out.send_dbl_prime_msg(
            header.to_bytes(2, "little") + data.to_bytes(4, "little")
        )

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
        usb_out.send_vendor_msg(tildagon_message)

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
        usb_in.send_vendor_msg(tildagon_message)
