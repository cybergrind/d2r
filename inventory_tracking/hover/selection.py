"""Conservative offline replay of the observed native inventory hit-test.

Only normal mouse layout, no carried item, no alternate inventory, and the
observed inventory widget vtable are supported. Results remain research candidates.
"""

import math
import struct

from inventory_tracking.items.containers import container_for_page
from inventory_tracking.items.owners import require_mercenary_owner
from inventory_tracking.tracking.state import select_player


def f32(value):
    value = struct.unpack('<f', struct.pack('<f', value))[0]
    if not math.isfinite(value) or abs(value) > 1_000_000:
        raise ValueError('Invalid UI float')
    return value


def _resolve(sample, base):
    ui = sample['after']
    snapshot = sample['snapshot']
    if not sample['ui_path_stable'] or not ui['process_stable'] or not ui['mappings_stable']:
        raise ValueError('Unstable UI/process')
    if snapshot['status'] != 'research' or snapshot['identity'] != ui['identity']:
        raise ValueError('Snapshot process mismatch')
    if not snapshot.get('mappings_stable') or not snapshot['groups']['items']['complete']:
        raise ValueError('Incomplete item traversal')
    native = ui['native']
    if native['errors']:
        raise ValueError('Native capture errors')
    records = native['blocks']
    by_address = {}
    for record in records:
        raw = bytes.fromhex(record['raw_hex'])
        after = bytes.fromhex(record['after_hex'])
        # Tooltip string allocation is not an input to the native hit-test.
        if record['label'] == 'mouse_widget':
            stable = len(raw) == len(after) == 0x700 and raw[:0x558] == after[:0x558] and raw[0x570:] == after[0x570:]
        else:
            stable = raw == after
        if not stable:
            raise ValueError(f'Changed native input: {record["label"]}')
        if record['address'] in by_address and by_address[record['address']] != raw:
            raise ValueError('Conflicting captured blocks')
        by_address[record['address']] = raw

    def block(address, size):
        raw = by_address[address]
        if len(raw) != size:
            raise ValueError('Unexpected native block size')
        return raw

    def unpack(fmt, raw, off=0):
        return struct.unpack_from(fmt, raw, off)[0]

    widget_info = ui['widgets']['mouse']
    if widget_info is None or ui['widgets']['controller'] is not None:
        raise ValueError('Unsupported focus state')
    equipment = widget_info['vtable'] == base + 0x17129D0 and widget_info['methods']['0xc0'] == base + 0x2178E0
    if not equipment and (
        widget_info['vtable'] != base + 0x1712DE8 or widget_info['methods']['0xc0'] != base + 0x21A6D0
    ):
        raise ValueError('Unsupported inventory widget')
    widget = block(widget_info['address'], 0x700)
    mouse = block(base + 0x1EC9C4D, 11)
    if mouse[0] or any(block(base + 0x1EC9F4C, 12)):
        raise ValueError('Unsupported mouse/carried-item state')
    if equipment:
        gx, gy = unpack('<i', widget, 0x5D8), 0
        if not 0 <= gx <= 12:
            raise ValueError('Invalid equipment slot')
        origin = None
    else:
        nodes = [widget]
        parent = unpack('<Q', widget, 0x30)
        seen = {widget_info['address']}
        while parent:
            if parent in seen or len(nodes) >= 17:
                raise ValueError('Invalid parent chain')
            seen.add(parent)
            raw = block(parent, 0x90)
            nodes.append(raw)
            parent = unpack('<Q', raw, 0x30)
        x = y = 0.0
        for i, raw in enumerate(nodes):
            if raw[0x52]:
                raise ValueError('Unsupported special layout')
            px, py = struct.unpack_from('<ii', raw, 0x70)
            x, y = f32(x + f32(px)), f32(y + f32(py))
            if i + 1 < len(nodes):
                next_node = nodes[i + 1]
                width, height = struct.unpack_from('<ii', next_node, 0x78)
                ax, ay = struct.unpack_from('<ff', raw, 0x48)
                scale = unpack('<f', next_node, 0x80)
                x = f32(f32(x + f32(f32(width) * ax)) * scale)
                y = f32(f32(y + f32(f32(height) * ay)) * scale)
        # sub_1415707ec rounds halfway away from zero; cell conversion uses floorf.
        origin = [math.copysign(math.floor(abs(v) + 0.5), v) for v in (x, y)]
        scale = 1.0
        for raw in reversed(nodes):
            factor = unpack('<f', raw, 0x80)
            if not 0 < factor <= 16:
                raise ValueError('Invalid UI scale')
            scale = f32(scale * factor)
        cw, ch = struct.unpack_from('<ii', widget, 0x5B8)
        if not 1 <= cw <= 4096 or not 1 <= ch <= 4096:
            raise ValueError('Invalid cell size')
        mx, my = struct.unpack_from('<ii', mouse, 3)
        gx = math.floor(f32(f32(mx - origin[0]) / f32(cw * scale)))
        gy = math.floor(f32(f32(my - origin[1]) / f32(ch * scale)))
    owner_id, owner_type = struct.unpack_from('<II', widget, 0x5C4)
    owners = [r for r in native['owners'] if r['type'] == owner_type and r['unit_id'] == owner_id]
    if len(owners) != 1 or owner_type not in (0, 1):
        raise ValueError('Unsupported or ambiguous inventory owner')
    owner = owners[0]
    header = block(owner['address'], 0xB0)
    if unpack('<I', header) != owner_type or unpack('<I', header, 8) != owner_id:
        raise ValueError('Owner header mismatch')
    if unpack('<Q', header, 0xA0) or unpack('<Q', header, 0x98):
        raise ValueError('Alternate inventory unsupported')
    inventory = block(unpack('<Q', header, 0x90), 0x48)
    if unpack('<I', inventory) != 0x1020304 or unpack('<Q', inventory, 8) != owner['address']:
        raise ValueError('Inventory owner mismatch')
    if unpack('<Q', inventory, 0x40):
        raise ValueError('Carried item unsupported')
    page = 255 if equipment else widget[0x630]
    if not equipment and page == 255:
        raise ValueError('Unsupported inventory container')
    container = container_for_page(page, owner_type=owner_type)
    if owner_type == 1 and not snapshot['groups'].get('monsters', {}).get('complete'):
        raise ValueError('Incomplete monster owner traversal')
    if page in (4, 255):
        if not snapshot['groups']['players']['complete']:
            raise ValueError('Incomplete stash owner traversal')
        player_id, _ = select_player(snapshot['groups']['players']['units'])
        if equipment and owner_type == 1:
            require_mercenary_owner(snapshot, owner_id, player_id)
        if equipment and owner_type == 0 and owner_id != player_id:
            raise ValueError('Equipment is not owned by the local player')
        if page == 4:
            container['name'] = 'Personal stash' if owner_id == player_id else 'Shared stash'
    array, count = struct.unpack_from('<QQ', inventory, 0x20)
    grid_index = 0 if equipment else page + 2
    if not grid_index < count <= 32:
        raise ValueError('Invalid inventory page')
    grid = block(array + grid_index * 32, 32)
    width, height = grid[0x10:0x12]
    if not 1 <= width <= 16 or not 1 <= height <= 16:
        raise ValueError('Invalid grid dimensions')
    if equipment and (width, height) != (13, 1):
        raise ValueError('Unexpected equipment grid dimensions')
    if owner_type == 1 and not equipment and (width, height) != (10, 10):
        raise ValueError('Unexpected shop grid dimensions')
    if owner_type == 0 and page == 3 and (width, height) != (3, 4):
        raise ValueError('Unexpected Cube grid dimensions')
    if page == 4 and (width, height) != (10, 10):
        raise ValueError('Unexpected stash grid dimensions')
    if not 0 <= gx < width or not 0 <= gy < height:
        raise ValueError('Outside supported inventory grid')
    cells = block(unpack('<Q', grid, 0x18), width * height * 8)
    pointer = unpack('<Q', cells, (gy * width + gx) * 8)
    result = {
        'validated': False,
        'cell': [gx, gy],
        'owner_id': owner_id,
        'origin': origin,
        'container': container,
        'owner_type': owner_type,
    }
    if not pointer:
        return dict(result, status='no_item')
    items = [u for u in snapshot['groups']['items']['units'] if u['address'] == pointer and u['type'] == 4]
    if len(items) != 1 or not items[0]['identity_stable']:
        raise ValueError('No unique stable item at native pointer')
    item = items[0]
    expected_item_owner = 0xFFFFFFFF if owner_type == 1 else owner_id
    if equipment and item['details']['body_location'] != gx:
        raise ValueError('Equipment slot mismatch')
    if (
        item['details']['owner_id'] != expected_item_owner
        or item['details']['inventory_page'] != page
        or item['mode'] != (1 if equipment else 0)
    ):
        raise ValueError('Item ownership/location mismatch')
    return dict(result, status='candidate', item=item)


def resolve_selection(sample, base):
    """Return a research candidate, explicit empty, or abstention with reason."""
    try:
        return _resolve(sample, base)
    except (ValueError, KeyError, TypeError, IndexError, struct.error, OverflowError) as exc:
        return {'status': 'unavailable', 'validated': False, 'reason': str(exc)}
