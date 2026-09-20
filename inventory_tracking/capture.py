"""Bounded sparse runtime capture and unvalidated unit-table signature leads.

Signature source: https://github.com/relentlessricktrinidad/d2go/blob/main/pkg/memory/offset.go
The displacement is module-relative, not RIP-relative. No old fixed RVA is used.
"""

import struct


MAX_CAPTURE = 64 * 1024 * 1024
SIGNATURE = bytes.fromhex('48 03 C7 49 8B 8C C6')


def capture_ranges(read, ranges, stream, *, max_bytes=MAX_CAPTURE, chunk_size=65536):
    if chunk_size <= 0 or any(end <= start for start, end in ranges):
        raise ValueError('Invalid capture ranges or chunk size')
    if sum(end - start for start, end in ranges) > max_bytes:
        raise ValueError('Capture exceeds byte budget')
    result = {'blocks': [], 'errors': [], 'bytes_read': 0}
    for start, end in ranges:
        for address in range(start, end, chunk_size):
            size = min(chunk_size, end - address)
            try:
                data = read(address, size)
                if len(data) > size:
                    raise ValueError('Reader returned more than requested')
            except OSError as exc:
                result['errors'].append({'address': address, 'size': size, 'error': str(exc)})
                continue
            if data:
                result['blocks'].append({'address': address, 'size': len(data), 'file_offset': stream.tell()})
                stream.write(data)
                result['bytes_read'] += len(data)
            if len(data) != size:
                result['errors'].append(
                    {'address': address + len(data), 'size': size - len(data), 'error': 'short read'}
                )
    return result


def scan_unit_table(blocks, base, image_size):
    """Scan only contiguous captured bytes, retaining boundary overlap."""
    tail = b''
    previous_end = None
    matches = []
    seen = set()
    for address, data in blocks:
        if previous_end != address:
            tail = b''
        combined = tail + data
        origin = address - len(tail)
        position = 0
        while (position := combined.find(SIGNATURE, position)) >= 0:
            if position + 11 <= len(combined):
                rva = struct.unpack_from('<i', combined, position + 7)[0]
                match_address = origin + position
                if 0 <= rva <= image_size - 5120 and match_address not in seen:
                    matches.append({'signature_address': match_address, 'table_rva': rva, 'table_address': base + rva})
                    seen.add(match_address)
            position += 1
        tail = combined[-10:]
        previous_end = address + len(data)
    return matches
