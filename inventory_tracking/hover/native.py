"""Raw inputs to the observed native inventory getter, not a hover decoder."""

import struct


def collect_native(read, base, ui, snapshot, *, all_grids=False):
    result = {'blocks': [], 'owners': [], 'errors': [], 'validated': False, 'stable': False}
    blocks = result['blocks']

    def capture(address, size, label):
        raw = read(address, size)
        if len(raw) != size:
            raise ValueError(f'Short native read: {label}')
        blocks.append({'address': address, 'label': label, 'raw_hex': raw.hex()})
        return raw

    def qword(raw, offset):
        return struct.unpack_from('<Q', raw, offset)[0]

    try:
        capture(base + 0x1EC9C4D, 11, 'mouse_gate_and_position')
        capture(base + 0x1EC9F4C, 12, 'carried_item_state')
        for label, widget in ui['widgets'].items():
            if not widget or 'raw_hex' not in widget:
                continue
            raw = capture(widget['address'], 0x700, f'{label}_widget')
            if raw != bytes.fromhex(widget['raw_hex']):
                result['errors'].append(f'{label} widget changed before native capture')
            parent = qword(raw, 0x30)
            seen = {widget['address']}
            for _ in range(16):
                if not parent:
                    break
                if parent in seen:
                    raise ValueError('UI parent cycle')
                seen.add(parent)
                parent_raw = capture(parent, 0x90, f'{label}_parent')
                parent = qword(parent_raw, 0x30)
            else:
                raise ValueError('UI parent depth exceeds bound')
            owner_id, owner_type = struct.unpack_from('<II', raw, 0x5C4)
            matches = [
                unit
                for group in snapshot.get('groups', {}).values()
                for unit in group['units']
                if unit['type'] == owner_type and unit['unit_id'] == owner_id and unit.get('identity_stable')
            ]
            if len(matches) != 1:
                raise ValueError('No unique stable typed UI owner')
            owner = matches[0]
            result['owners'].append({'address': owner['address'], 'type': owner_type, 'unit_id': owner_id})
            header = capture(owner['address'], 0xB0, f'{label}_owner')
            if struct.unpack_from('<I', header)[0] != owner_type or struct.unpack_from('<I', header, 8)[0] != owner_id:
                raise ValueError('UI owner identity changed')
            # Native getter may use +98 via a reference object at +a0, otherwise +90.
            # Preserve both candidates; never choose based on a plausible-looking grid.
            page = raw[0x630]
            if page > 15 and not all_grids and widget.get('vtable') != base + 0x17129D0:
                raise ValueError('UI page exceeds research bound')
            for offset in (0x90, 0x98):
                address = qword(header, offset)
                if not address:
                    continue
                inventory = capture(address, 0x48, f'{label}_inventory_{offset:x}')
                if struct.unpack_from('<I', inventory)[0] != 0x1020304:
                    continue
                grid_array, count = struct.unpack_from('<QQ', inventory, 0x20)
                if count > 32:
                    raise ValueError('Inventory grid count exceeds bound')
                if not grid_array:
                    continue
                equipment = widget.get('vtable') == base + 0x17129D0
                indices = range(count) if all_grids else [0 if equipment else page + 2]
                for index in indices:
                    if index >= count:
                        continue
                    suffix = f'{offset:x}' if index == page + 2 else f'{offset:x}_index{index}'
                    grid = capture(grid_array + index * 32, 32, f'{label}_grid_{suffix}')
                    width, height = grid[0x10:0x12]
                    cells = qword(grid, 0x18)
                    if not cells:
                        continue
                    if not 1 <= width <= 16 or not 1 <= height <= 16:
                        raise ValueError('Inventory grid dimensions exceed bound')
                    capture(cells, width * height * 8, f'{label}_cells_{suffix}')

    except (OSError, ValueError) as exc:
        result['errors'].append(str(exc))
    for block in reversed(blocks):
        try:
            block['after_hex'] = read(block['address'], len(bytes.fromhex(block['raw_hex']))).hex()
        except (OSError, ValueError) as exc:
            block['error'] = str(exc)
            result['errors'].append(str(exc))
    result['stable'] = not result['errors'] and all(b['raw_hex'] == b.get('after_hex') for b in blocks)
    return result
