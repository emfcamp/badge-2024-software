# eeprom_i2c.py MicroPython driver for Microchip I2C EEPROM devices.

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2019-2024 Peter Hinch

# Thanks are due to Abel Deuring for help in diagnosing and fixing a page size issue.

import time
from micropython import const
from bdevice import EepromDevice

_ADDR = const(0x50)  # Base address of chip
_MAX_CHIPS_COUNT = const(8)  # Max number of chips

T24C512 = const(65536)  # 64KiB 512Kbits
T24C256 = const(32768)  # 32KiB 256Kbits
T24C128 = const(16384)  # 16KiB 128Kbits
T24C64 = const(8192)  # 8KiB 64Kbits
T24C32 = const(4096)  # 4KiB 32Kbits


# Logical EEPROM device consists of 1-8 physical chips. Chips must all be the
# same size, and must have contiguous addresses.
class EEPROM(EepromDevice):
    def __init__(
        self,
        i2c,
        chip_size=T24C512,
        verbose=True,
        block_size=9,
        addr=_ADDR,
        max_chips_count=_MAX_CHIPS_COUNT,
        page_size=None,
    ):
        self._i2c = i2c
        if chip_size not in (T24C32, T24C64, T24C128, T24C256, T24C512):
            print("Warning: possible unsupported chip. Size:", chip_size)
        # Get no. of EEPROM chips
        nchips, min_chip_address = self.scan(verbose, chip_size, addr, max_chips_count)
        self._min_chip_address = min_chip_address
        self._i2c_addr = 0  # I2C address of current chip
        self._buf1 = bytearray(1)
        self._addrbuf = bytearray(2)  # Memory offset into current chip
        self._onebyte = chip_size <= 256  # Single byte address
        # superclass figures out _page_size and _page_mask
        super().__init__(block_size, nchips, chip_size, page_size, verbose)

    # Check for a valid hardware configuration
    def scan(self, verbose, chip_size, addr, max_chips_count):
        devices = self._i2c.scan()  # All devices on I2C bus
        eeproms = [
            d for d in devices if addr <= d < addr + max_chips_count
        ]  # EEPROM chips
        nchips = len(eeproms)
        if nchips == 0:
            raise RuntimeError("EEPROM not found.")
        eeproms = sorted(eeproms)
        if len(set(eeproms)) != len(eeproms):
            raise RuntimeError("Duplicate addresses were found", eeproms)
        if (eeproms[-1] - eeproms[0] + 1) != len(eeproms):
            raise RuntimeError("Non-contiguous chip addresses", eeproms)
        if verbose:
            s = "{} chips detected. Total EEPROM size {}bytes."
            print(s.format(nchips, chip_size * nchips))
        return nchips, min(eeproms)

    def _wait_rdy(self):  # After a write, wait for device to become ready
        self._buf1[0] = 0
        while True:
            try:
                if self._i2c.writeto(self._i2c_addr, self._buf1):  # Poll ACK
                    break
            except OSError:
                pass
            finally:
                time.sleep_ms(1)

    # Given an address, set ._i2c_addr and ._addrbuf and return the number of
    # bytes that can be processed in the current page
    def _getaddr(self, addr, nbytes):  # Set up _addrbuf and _i2c_addr
        if addr >= self._a_bytes:
            raise RuntimeError("EEPROM Address is out of range")
        ca, la = divmod(addr, self._c_bytes)  # ca == chip no, la == offset into chip
        self._addrbuf[0] = (la >> 8) & 0xFF
        self._addrbuf[1] = la & 0xFF
        self._i2c_addr = self._min_chip_address + ca
        pe = (la & self._page_mask) + self._page_size  # byte 0 of next page
        return min(nbytes, pe - la)

    # Read or write multiple bytes at an arbitrary address
    def readwrite(self, addr, buf, read):
        nbytes = len(buf)
        mvb = memoryview(buf)
        start = 0  # Offset into buf.
        while nbytes > 0:
            npage = self._getaddr(addr, nbytes)  # No. of bytes in current page
            # assert npage > 0
            # Offset address into chip: one or two bytes
            vaddr = self._addrbuf[1:] if self._onebyte else self._addrbuf
            if read:
                try:
                    self._i2c.writeto(self._i2c_addr, vaddr)
                    self._i2c.readfrom_into(self._i2c_addr, mvb[start : start + npage])
                except OSError:
                    # failure - possibly a hexpansion has been removed
                    nbytes = 0
            else:
                try:
                    self._i2c.writevto(
                        self._i2c_addr, (vaddr, buf[start : start + npage])
                    )
                except OSError:
                    # failure - possibly a hexpansion has been removed
                    nbytes = 0
                self._wait_rdy()
            nbytes -= npage
            start += npage
            addr += npage
        return buf
