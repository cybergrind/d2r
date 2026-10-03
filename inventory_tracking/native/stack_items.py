"""Currency-tab stack counts verified against the 20260925T124336Z capture."""

import struct


STACK_COUNT_OFFSET = 0x9C


def read_stack_count(read, unit) -> int:
    return struct.unpack('<I', read(unit['data_pointer'] + STACK_COUNT_OFFSET, 4))[0]
