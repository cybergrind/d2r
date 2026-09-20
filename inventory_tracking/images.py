"""Bounded PE32+ header discovery, without assuming named Wine mappings.

Format: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
Header matches identify research candidates, not verified runtime code or layouts.
"""

import struct


MAX_HEADER = 65536
MAX_CANDIDATES = 16384


def read_pe(read):
    """Parse x64 PE metadata through an exact, relative-offset reader."""

    def exact(offset, size):
        if offset < 0 or offset + size > MAX_HEADER:
            raise ValueError('PE headers exceed 64 KiB bound')
        data = read(offset, size)
        if len(data) != size:
            raise ValueError('Short PE header read')
        return data

    dos = exact(0, 64)
    if dos[:2] != b'MZ':
        raise ValueError('Missing DOS signature')
    offset = struct.unpack_from('<I', dos, 60)[0]
    header = exact(offset, 24)
    if offset < 64 or header[:4] != b'PE\0\0':
        raise ValueError('Invalid PE signature')
    machine, count, stamp = struct.unpack_from('<HHI', header, 4)
    optional_size = struct.unpack_from('<H', header, 20)[0]
    if machine != 0x8664 or not 1 <= count <= 96 or not 112 <= optional_size <= 4096:
        raise ValueError('Unsupported PE architecture or header dimensions')
    optional = exact(offset + 24, optional_size)
    if struct.unpack_from('<H', optional)[0] != 0x20B:
        raise ValueError('Expected PE32+')
    entry = struct.unpack_from('<I', optional, 16)[0]
    base = struct.unpack_from('<Q', optional, 24)[0]
    image_size, header_size = struct.unpack_from('<II', optional, 56)
    section_offset = offset + 24 + optional_size
    if not section_offset + count * 40 <= header_size <= MAX_HEADER or not header_size <= image_size <= 2**32 - 1:
        raise ValueError('Invalid image/header size')
    if entry >= image_size:
        raise ValueError('Entrypoint outside image')
    table = exact(section_offset, count * 40)
    sections = []
    for index in range(count):
        pos = index * 40
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from('<IIII', table, pos + 8)
        if rva + max(virtual_size, raw_size) > image_size:
            raise ValueError('Section outside image')
        sections.append(
            {
                'name': table[pos : pos + 8].rstrip(b'\0').decode('ascii', errors='replace'),
                'rva': rva,
                'virtual_size': virtual_size,
                'raw_size': raw_size,
                'raw_offset': raw_offset,
                'characteristics': struct.unpack_from('<I', table, pos + 36)[0],
            }
        )
    return {
        'machine': machine,
        'timestamp': stamp,
        'preferred_base': base,
        'image_size': image_size,
        'header_size': header_size,
        'entry_rva': entry,
        'sections': sections,
    }


def discover_images(read, mappings, disk, *, max_candidates=MAX_CANDIDATES):
    """Inspect mapping starts and the disk preferred base; never scan arbitrary pages."""
    readable = sorted(
        (m for m in mappings if m['permissions'].startswith('r') and not m['path'].startswith(('[vvar', '[vsyscall'))),
        key=lambda m: m['start'],
    )
    addresses = {m['start'] for m in readable}
    if disk:
        addresses.add(disk['preferred_base'])
    addresses = sorted(addresses)
    result = {
        'status': 'unavailable',
        'images': [],
        'attempted': 0,
        'rejected': 0,
        'method': 'readable mapping starts plus disk preferred base',
        'candidate_limit': max_candidates,
    }

    def mapped_read(address, size):
        end = address + size
        cursor = address
        for mapping in readable:
            if mapping['start'] <= cursor < mapping['end']:
                cursor = min(end, mapping['end'])
                if cursor == end:
                    return read(address, size)
        raise ValueError('Header read crosses unreadable or unmapped memory')

    for base in addresses[:max_candidates]:
        result['attempted'] += 1
        try:
            pe = read_pe(lambda offset, size, base=base: mapped_read(base + offset, size))
        except OSError, ValueError:
            result['rejected'] += 1
            continue
        code_ranges = executable_ranges(base, pe)
        code_mapped = bool(code_ranges) and all(
            executable_range_mapped(readable, start, size) for start, size in code_ranges
        )
        entry = base + pe['entry_rva']
        entry_executable = any(
            start <= entry < start + size for start, size in code_ranges
        ) and executable_range_mapped(readable, entry, 1)
        result['images'].append(
            {
                'base': base,
                'pe': pe,
                'disk_header_match': disk is not None and pe == disk,
                'executable_sections_mapped': code_mapped,
                'entry_executable': entry_executable,
            }
        )
        if result['images'][-1]['disk_header_match']:
            result['images'][-1]['mapping_evidence'] = image_mapping_evidence(readable, base, pe)
    matches = [image for image in result['images'] if image['disk_header_match'] and image['entry_executable']]
    if len(addresses) > max_candidates:
        result['status'] = 'incomplete'
    elif len(matches) > 1:
        result['status'] = 'ambiguous'
    elif len(matches) == 1:
        result.update(status='candidate', candidate_base=matches[0]['base'])
    return result


def executable_ranges(base, pe):
    return [
        (base + section['rva'], section['virtual_size'])
        for section in pe['sections']
        if section['characteristics'] & 0x20000000 and section['virtual_size']
    ]


def image_mapping_evidence(mappings, base, pe):
    """Bounded mapping metadata for debugging rejected loaded-image candidates."""
    end = base + pe['image_size']
    overlaps = [m for m in mappings if m['start'] < end and m['end'] > base]
    entry = base + pe['entry_rva']
    return {
        'entry_address': entry,
        'entry_mappings': [m for m in overlaps if m['start'] <= entry < m['end']],
        'readable_mappings': overlaps[:128],
        'mapping_count': len(overlaps),
        'truncated': len(overlaps) > 128,
    }


def executable_range_mapped(mappings, start, size):
    end = start + size
    cursor = start
    for mapping in mappings:
        if mapping['start'] <= cursor < mapping['end']:
            if 'x' not in mapping['permissions'] or not mapping['permissions'].startswith('r'):
                return False
            cursor = min(end, mapping['end'])
            if cursor == end:
                return True
    return False
