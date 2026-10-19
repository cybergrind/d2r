"""Fake game memory for the readers' tests: zeroed blocks at addresses, read back like `/proc/<pid>/mem`."""


class Memory:
    def __init__(self):
        self.blocks = {}

    def block(self, address, size):
        """A zeroed block of `size` bytes at `address`, to fill in place."""
        self.blocks[address] = bytearray(size)
        return self.blocks[address]

    def read(self, address, size):
        for start, data in self.blocks.items():
            if start <= address and address + size <= start + len(data):
                return bytes(data[address - start : address - start + size])
        raise ValueError(f'Unmapped or unreadable range at {address:#x}')
