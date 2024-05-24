from eeprom_i2c import EEPROM


class EEPROMPartition:
    def __init__(self, eep: EEPROM, offset: int, length: int):
        # It me. I'm eepy. Pls give eep
        self.eepy = eep
        self.partition_offset = offset
        self.partition_length = length
        self._block_size = self.eepy._block_size

    def readblocks(self, block_num, buf, offset=0):
        addr = block_num * self._block_size + offset + self.partition_offset
        buf[:] = self.eepy[addr : addr + len(buf)]

    def writeblocks(self, block_num, buf, offset=0):
        addr = block_num * self._block_size + offset + self.partition_offset
        self.eepy[addr : addr + len(buf)] = buf

    def ioctl(self, op, arg):
        if op == 3:  # synchronize
            self.eepy.sync()
            return
        if op == 4:  # block count
            return self.partition_length // self._block_size
        if op == 5:  # block size
            return self._block_size
        if op == 6:  # erase handled by driver (?)
            return 0
