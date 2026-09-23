"""Bounded, unvalidated inventory UI observations; never a selection verdict.

Supported-build runtime evidence: sub_1401ed340 and sub_1402197f0 follow
[image+1ee5790] -> +d0 -> +178 (mouse) / +190 (controller). See hover_research.md.
"""

import struct


UI_MANAGER_RVA = 0x1EE5790
WIDGET_BYTES = 0x700


def collect_ui(read, base, image_size):
    result = {'validated': False, 'stable': False, 'anchors': [], 'widgets': {}, 'errors': []}
    anchors = result['anchors']

    def pointer(address):
        raw = read(address, 8)
        if len(raw) != 8:
            raise ValueError('Short UI pointer read')
        anchors.append({'address': address, 'before_hex': raw.hex()})
        return struct.unpack('<Q', raw)[0]

    try:
        manager = pointer(base + UI_MANAGER_RVA)
        result['manager'] = manager
        context = pointer(manager + 0xD0) if manager else 0
        result['context'] = context
        for label, offset in (('mouse', 0x178), ('controller', 0x190)):
            address = pointer(context + offset) if context else 0
            result['widgets'][label] = None
            if not address:
                continue
            widget = {'address': address}
            result['widgets'][label] = widget
            try:
                raw = read(address, WIDGET_BYTES)
                if len(raw) != WIDGET_BYTES:
                    raise ValueError('Short UI widget read')
                widget['raw_hex'] = raw.hex()
                vtable = struct.unpack_from('<Q', raw)[0]
                widget['vtable'] = vtable
                widget['vtable_in_image'] = base <= vtable <= base + image_size - 0x118
                # Only read a small in-image method table; never execute game code.
                if widget['vtable_in_image']:
                    table = read(vtable, 0x118)
                    if len(table) != 0x118:
                        raise ValueError('Short UI vtable read')
                    widget['methods'] = {
                        hex(off): struct.unpack_from('<Q', table, off)[0]
                        for off in (0x58, 0x90, 0xB8, 0xC0, 0xF0, 0xF8, 0x100, 0x110)
                    }
                after = read(address, WIDGET_BYTES)
                widget['after_hex'] = after.hex()
                widget['bytes_stable'] = raw == after
                # Changing visual fields are retained, not treated as identity evidence.
                widget['vtable_stable'] = raw[:8] == after[:8] and len(after) == WIDGET_BYTES
            except (OSError, ValueError) as exc:
                widget['error'] = str(exc)
                result['errors'].append(str(exc))
    except (OSError, ValueError) as exc:
        result['errors'].append(str(exc))
    for anchor in reversed(anchors):
        try:
            anchor['after_hex'] = read(anchor['address'], 8).hex()
        except (OSError, ValueError) as exc:
            anchor['error'] = str(exc)
            result['errors'].append(str(exc))
    result['stable'] = (
        not result['errors']
        and all(row['before_hex'] == row.get('after_hex') for row in anchors)
        and all(row is None or row.get('vtable_stable') for row in result['widgets'].values())
    )
    return result
