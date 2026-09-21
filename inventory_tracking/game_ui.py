"""Build-specific UI signature and blocking-menu sampling for potion input.

Lead: d2go memory/offset.go and game_reader.go; observed signature in this build
at 0x140ce0df4 resolves UI flag at 0x141ebd176. Never adopt a fixed absolute pointer.
"""

import struct


UI_SIGNATURE = bytes.fromhex('40 84 ed 0f 94 05')
BLOCKING_FLAGS = (1, 2, 3, 4, 5, 7, 8, 9, 0x0B, 0x0D, 0x0E, 0x13, 0x18, 0x19, 0x1E, 0x168)


def scan_ui_flags(blocks, base, image_size):
    tail = b''
    previous_end = None
    addresses = set()
    for address, data in blocks:
        if previous_end != address:
            tail = b''
        combined = tail + data
        origin = address - len(tail)
        position = 0
        while (position := combined.find(UI_SIGNATURE, position)) >= 0:
            if position + 10 <= len(combined):
                target = origin + position + 10 + struct.unpack_from('<i', combined, position + 6)[0] - 10
                if base <= target <= base + image_size - 0x16D:
                    addresses.add(target)
            position += 1
        tail = combined[-9:]
        previous_end = address + len(data)
    return sorted(addresses)


def read_ui_state(read, candidates):
    if len(candidates) != 1:
        return {'ready': False, 'reason': 'UI location unavailable'}
    before = read(candidates[0], 0x16D)
    after = read(candidates[0], 0x16D)
    flags = {hex(offset): before[offset] for offset in BLOCKING_FLAGS}
    ready = before == after and all(value == 0 for value in flags.values())
    return {'ready': ready, 'flags': flags, 'stable': before == after}
