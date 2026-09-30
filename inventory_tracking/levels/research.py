"""Win+C research dump: which level/room structures the client holds right now.

Question under study: does the client keep the whole current level (every Room2 and
its presets, e.g. the Arcane Sanctuary arm with the Summoner) or only the Room1s
streamed around the player? The dump answers it from memory without deciding it.

Layout leads, NOT validated on the supported build (third-parties/, 2026-09-30):
- unit +0x20 act, +0x38 path; path +0x02/+0x06 dynamic x/y, +0x10/+0x14 static
  x/y, +0x20 Room1 (MapAssist Structs/UnitAny.cs, Structs/Path.cs).
- Room1 +0x00 near-room array, +0x18 Room2, +0x40 near count, +0x48 act,
  +0xA8 first unit, +0xB0 next Room1 (MapAssist Structs/Room.cs).
- Room2 +0x90 level; level +0x1F8 area ID (d2go pkg/memory/player.go).
- Act +0x1C map seed (zero since the seed was hidden), +0x28 act ID, +0x78 ActMisc;
  ActMisc +0x830 difficulty, +0x840 init seed hash, +0x868 end seed hash,
  +0x870 first level (MapAssist Structs/Act.cs, Structs/ActMisc.cs).
The Room2 list and next-level links have no D2R reference: they are found by
back-pointer (a Room2 whose +0x90 is the level), and every candidate offset is kept.
Seed hashes are recorded as observed; nothing here decodes a seed or generates a map.
"""

import os
import struct
from typing import Any

from inventory_tracking.loot.runes import RUNES
from inventory_tracking.loot.shrines import SHRINE_NAMES
from inventory_tracking.native.layout import OBJECT_SHRINE_TABLE, OBJECT_SHRINE_TYPE
from inventory_tracking.native.process import identity, process_mappings
from inventory_tracking.native.unit_probe import ResearchReader
from inventory_tracking.native.units import walk_units


# d2data monstats.json *hcIdx 250 = summoner; objects.json 357 = "yet another tome"
# (Horazon's Journal; MapAssist GameObject.YetAnotherTome); levels.json 74 = Arcane.
SUMMONER_MONSTER = 250
JOURNAL_OBJECT = 357
ARCANE_SANCTUARY = 74
MARKERS = {'summoner_monster': (SUMMONER_MONSTER, 1), 'journal_object': (JOURNAL_OBJECT, 2)}

UNIT_GROUPS = ((0, 'players'), (1, 'monsters'), (2, 'objects'), (4, 'ground_items'), (5, 'tiles'))
GROUND_MODES = frozenset((3, 5))  # items on the ground / dropping (MapAssist ItemMode; unconfirmed here)
LEVEL_SIZE = 0x400
ROOM_SIZE = 0x100
BLOCK_SIZE = 0x80
MAX_ROOMS = 2048
MAX_LEVELS = 256
MAX_BLOCKS_PER_ROOM = 48
READ_BUDGET = 48 * 1024 * 1024


def valid_pointer(value):
    return 0x10000 <= value < 2**47 and value % 8 == 0


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def u64(data, offset):
    return struct.unpack_from('<Q', data, offset)[0]


def u16(data, offset):
    return struct.unpack_from('<H', data, offset)[0]


class Probe:
    """Tolerant reads: an unmapped candidate pointer is data, not a failure."""

    def __init__(self, read):
        self.read = read

    def get(self, address, size):
        if not valid_pointer(address):
            return None
        try:
            data = self.read(address, size)
        except OSError, ValueError:
            return None
        return data if len(data) == size else None

    def pointer(self, address):
        data = self.get(address, 8)
        return None if data is None else u64(data, 0)

    def level_no(self, level):
        data = self.get(level + 0x1F8, 4)
        return None if data is None else u32(data, 0)


def room2_level(probe, room2):
    return probe.pointer(room2 + 0x90)


def room2_lists(probe, level, level_bytes, *, max_rooms=MAX_ROOMS):
    """Every (level field, Room2 next field) pair that walks Room2s pointing back at the level."""
    lists = []
    for first_offset in range(0, len(level_bytes), 8):
        first = u64(level_bytes, first_offset)
        if first == level or room2_level(probe, first) != level:
            continue
        head = probe.get(first, ROOM_SIZE)
        if head is None:
            continue
        for next_offset in range(0, ROOM_SIZE, 8):
            second = u64(head, next_offset)
            if second == first or room2_level(probe, second) != level:
                continue
            rooms, seen, cursor = [], set(), first
            while cursor and cursor not in seen and len(rooms) < max_rooms:
                if room2_level(probe, cursor) != level:
                    break
                seen.add(cursor)
                rooms.append(cursor)
                cursor = probe.pointer(cursor + next_offset) or 0
            lists.append({'level_offset': first_offset, 'next_offset': next_offset, 'rooms': rooms})
        if not any(item['level_offset'] == first_offset for item in lists):
            lists.append({'level_offset': first_offset, 'next_offset': None, 'rooms': [first]})
    lists.sort(key=lambda item: -len(item['rooms']))
    return lists


def level_chain(probe, first, *, max_levels=MAX_LEVELS):
    """Follow the next-level field that yields the most distinct plausible area IDs."""
    head = probe.get(first, LEVEL_SIZE)
    if head is None:
        return {'offset': None, 'levels': []}
    best = {'offset': None, 'levels': [first]}
    for offset in range(0, LEVEL_SIZE, 8):
        second = u64(head, offset)
        if second == first or not 1 <= (probe.level_no(second) or 0) <= 200:
            continue
        levels, cursor = [], first
        while cursor and cursor not in levels and len(levels) < max_levels:
            if not 1 <= (probe.level_no(cursor) or 0) <= 200:
                break
            levels.append(cursor)
            cursor = probe.pointer(cursor + offset) or 0
        if len(levels) > len(best['levels']):
            best = {'offset': offset, 'levels': levels}
    return best


def loaded_room1s(probe, start, *, max_rooms=MAX_ROOMS):
    """Room1s reachable through near-room arrays and next links from the player's room."""
    rooms, queue = {}, [start]
    while queue and len(rooms) < max_rooms:
        room = queue.pop()
        if room in rooms:
            continue
        data = probe.get(room, ROOM_SIZE)
        if data is None:
            continue
        near_pointer, near_count = u64(data, 0x00), u32(data, 0x40)
        near = []
        if 0 < near_count <= 64:
            array = probe.get(near_pointer, near_count * 8)
            near = list(struct.unpack(f'<{near_count}Q', array)) if array else []
        room2 = u64(data, 0x18)
        level = room2_level(probe, room2)
        rooms[room] = {
            'room2': room2,
            'level': level,
            'level_no': None if level is None else probe.level_no(level),
            'near': len(near),
            'first_unit': u64(data, 0xA8),
        }
        queue.extend(p for p in (*near, u64(data, 0xB0)) if valid_pointer(p) and p not in rooms)
    return rooms


MAX_MASK_BYTES = 128 * 1024  # a 24x24-tile cave room is 120x120 sub-tiles = 28.8 KB of u16
MAX_MASK_VALUES = 16  # collision cells are a few flag combinations


def collision_candidates(probe, room1, room2):
    """Research: where the Room1 keeps its collision mask (walkable vs blocked sub-tiles).

    D2MOO's ActiveRoom points at a collision grid holding the room's sub-tile bounds and a
    u16 mask of width x height cells. Look for the Room2's bounds x5 (tiles -> sub-tiles, the
    unit of player positions) in the Room1 and in each block it points at, then for a pointer
    beside them that reads as a width x height u16 array. Every match is kept, with its mask.
    """
    room1_data, bounds = probe.get(room1, ROOM_SIZE), probe.get(room2 + 0x60, 16) if room2 else None
    if room1_data is None or bounds is None:
        return []
    x, y, w, h = (v * 5 for v in struct.unpack('<IIII', bounds))
    wanted = struct.pack('<IIII', x, y, w, h)
    if not 0 < w * h * 2 <= MAX_MASK_BYTES:
        return []
    sources = [(None, room1, room1_data)]
    for offset in range(0, ROOM_SIZE, 8):
        target = u64(room1_data, offset)
        data = probe.get(target, BLOCK_SIZE)
        if data is not None:
            sources.append((offset, target, data))
    found = []
    for room1_offset, _, data in sources:
        coords = data.find(wanted)
        if coords < 0 or coords % 4:
            continue
        for mask_offset in range(0, len(data) - 7, 8):
            mask = probe.get(u64(data, mask_offset), w * h * 2)
            if mask is None:
                continue
            values = {}
            for (cell,) in struct.iter_unpack('<H', mask):
                values[str(cell)] = values.get(str(cell), 0) + 1
            if len(values) > MAX_MASK_VALUES:
                continue  # arbitrary data, not a mask of a few collision flags
            found.append(
                {
                    'room1_offset': room1_offset,
                    'coords_offset': coords,
                    'mask_offset': mask_offset,
                    'origin': [x, y],
                    'size': [w, h],
                    'values': values,
                    'mask_hex': mask.hex(),
                }
            )
    return found


def marker_hits(data, base):
    """Marker IDs with the matching unit type within 16 bytes (the legacy preset shape)."""
    hits = []
    for offset in range(0, len(data) - 3, 4):
        value = u32(data, offset)
        for name, (marker, unit_type) in MARKERS.items():
            if value != marker:
                continue
            window = range(max(0, offset - 16), min(len(data) - 3, offset + 17), 4)
            typed = any(u32(data, o) == unit_type for o in window if o != offset)
            hits.append({'marker': name, 'address': base + offset, 'typed': typed})
    return hits


def room2_blocks(probe, room2, known, *, max_blocks=MAX_BLOCKS_PER_ROOM):
    """Room2 bytes plus pointer targets up to depth 3, skipping other rooms/levels/acts."""
    blocks, queue = [], [(room2, ROOM_SIZE, 0)]
    seen = {room2}
    while queue and len(blocks) < max_blocks:
        address, size, depth = queue.pop(0)
        data = probe.get(address, size)
        if data is None:
            continue
        blocks.append({'address': address, 'depth': depth, 'hex': data.hex(), 'hits': marker_hits(data, address)})
        if depth == 3:
            continue
        for offset in range(0, size, 8):
            target = u64(data, offset)
            if valid_pointer(target) and target not in seen and target not in known:
                seen.add(target)
                queue.append((target, BLOCK_SIZE, depth + 1))
    return blocks


OBJECT_DATA_SIZE = 0x40


def shrine_candidate(data: bytes):
    """Shrine type and table pointer from an object's data block (layout.py, confirmed 2026-09-30)."""
    shrine_type = data[OBJECT_SHRINE_TYPE]
    table = struct.unpack_from('<Q', data, OBJECT_SHRINE_TABLE)[0]
    if not valid_pointer(table) or shrine_type >= len(SHRINE_NAMES):
        return None
    return {'type': shrine_type, 'name': SHRINE_NAMES[shrine_type], 'table': table}


def unit_record(probe, unit, *, dynamic):
    raw = probe.get(unit['address'], 0x160)
    record = {key: unit[key] for key in ('address', 'type', 'txt_id', 'unit_id', 'mode')}
    if raw is None:
        return record | {'error': 'unit reread failed'}
    record['act'] = u64(raw, 0x20)
    path = probe.get(u64(raw, 0x38), 0x28)
    if path is not None:
        record['x'], record['y'] = (u16(path, 0x02), u16(path, 0x06)) if dynamic else (u16(path, 0x10), u16(path, 0x14))
        record['room1'] = u64(path, 0x20)
    if unit['type'] == 2:  # objects: keep the data block for offset research (shrines)
        data = probe.get(u64(raw, 0x10), OBJECT_DATA_SIZE)
        record['data_hex'] = data.hex() if data is not None else None
        record['shrine_candidate'] = shrine_candidate(data) if data is not None else None
    return record


def act_record(probe, act):
    data = probe.get(act, 0x80)
    if data is None:
        return {'address': act, 'error': 'act unreadable'}
    result: dict[str, Any] = {
        'address': act,
        'map_seed_field': u32(data, 0x1C),
        'act_id': u32(data, 0x28),
        'act_misc': u64(data, 0x78),
    }
    misc = probe.get(result['act_misc'], 0x878)
    if misc is not None:
        result.update(
            difficulty=u32(misc, 0x830),
            init_seed_hash=u64(misc, 0x840),
            end_seed_hash=u32(misc, 0x868),
            misc_act_matches=u64(misc, 0x860) == act,
            first_level=u64(misc, 0x870),
        )
    return result


def survey(read, table_address) -> dict[str, Any]:
    probe = Probe(read)
    units: dict[str, list[dict[str, Any]]] = {}
    errors = {}
    for unit_type, label in UNIT_GROUPS:
        heads = probe.get(table_address + unit_type * 1024, 1024)
        if heads is None:
            errors[label] = 'table unreadable'
            units[label] = []
            continue
        group = walk_units(read, struct.unpack('<128Q', heads), unit_type)
        errors[label] = group['errors']
        members = group['units']
        if unit_type == 4:  # only ground items: inventory/stash items are thousands and not level data
            members = [u for u in members if u['mode'] in GROUND_MODES]
        units[label] = [unit_record(probe, u, dynamic=unit_type in (0, 1)) for u in members]

    player = next((p for p in units['players'] if p.get('room1')), None)
    if player is None:
        raise ValueError('No player unit with a room; is a character in game?')
    room1s = loaded_room1s(probe, player['room1'])
    current = room1s.get(player['room1'], {})
    level = current.get('level')
    act = act_record(probe, player['act'])
    for address, record in room1s.items():  # walkability research (levels/plan.md), current level only
        if record['level'] == level:
            record['collision'] = collision_candidates(probe, address, record['room2'])

    level_bytes = probe.get(level, LEVEL_SIZE) if level else None
    lists = room2_lists(probe, level, level_bytes) if level_bytes else []
    rooms = lists[0]['rooms'] if lists else []
    loaded_room2s = {r['room2'] for r in room1s.values()}
    known = set(room1s) | loaded_room2s | set(rooms) | {level, player['act'], act.get('act_misc')}
    room2s = []
    for index, room2 in enumerate(rooms):
        blocks = room2_blocks(probe, room2, known - {room2})
        room2s.append(
            {
                'index': index,
                'address': room2,
                'has_loaded_room1': room2 in loaded_room2s,
                'hits': [h for b in blocks for h in b['hits']],
                'blocks': blocks,
            }
        )

    levels = []
    chain = level_chain(probe, act['first_level']) if valid_pointer(act.get('first_level', 0)) else None
    for address in (chain or {}).get('levels', []):
        data = probe.get(address, LEVEL_SIZE)
        found = room2_lists(probe, address, data) if data else []
        levels.append(
            {
                'address': address,
                'level_no': probe.level_no(address),
                'room2_count': len(found[0]['rooms']) if found else 0,
                'loaded_room1_count': sum(r['level'] == address for r in room1s.values()),
            }
        )

    markers = {
        'summoner_units': [m for m in units['monsters'] if m['txt_id'] == SUMMONER_MONSTER],
        'journal_units': [o for o in units['objects'] if o['txt_id'] == JOURNAL_OBJECT],
        'typed_room2_hits': [
            {'room2_index': r['index'], 'has_loaded_room1': r['has_loaded_room1'], **h}
            for r in room2s
            for h in r['hits']
            if h['typed']
        ],
    }
    summary = {
        'level_no': current.get('level_no'),
        'player': {k: player.get(k) for k in ('x', 'y')},
        'difficulty': act.get('difficulty'),
        'loaded_room1s': len(room1s),
        'loaded_room1s_in_level': sum(r['level'] == level for r in room1s.values()),
        'room2s_in_level': len(rooms),
        'room2s_with_room1': sum(r['has_loaded_room1'] for r in room2s),
        'levels_in_act_chain': len(levels),
        'levels_with_room2s': sum(lv['room2_count'] > 0 for lv in levels),
        'units': {label: len(items) for label, items in units.items()},
        'summoner_unit_seen': bool(markers['summoner_units']),
        'journal_unit_seen': bool(markers['journal_units']),
        'typed_marker_hits': len(markers['typed_room2_hits']),
        'ground_items': [
            {k: o.get(k) for k in ('txt_id', 'mode', 'x', 'y')}
            | {'rune': RUNES[o['txt_id']]['name'] if o['txt_id'] in RUNES else None}
            for o in units.get('ground_items', [])
        ],
        'collision_rooms': sum(bool(r.get('collision')) for r in room1s.values()),
        'shrine_candidates': [
            {'txt_id': o['txt_id'], 'x': o.get('x'), 'y': o.get('y')}
            | {k: o['shrine_candidate'][k] for k in ('type', 'name')}
            for o in units.get('objects', [])
            if o.get('shrine_candidate')
        ],
    }
    return {
        'status': 'research',
        'validated': False,
        'summary': summary,
        'markers': markers,
        'act': act,
        'level': {
            'address': level,
            'hex': level_bytes.hex() if level_bytes else None,
            'room2_list_candidates': [
                {k: v for k, v in item.items() if k != 'rooms'} | {'count': len(item['rooms'])} for item in lists
            ],
        },
        'levels': levels,
        'level_chain_offset': (chain or {}).get('offset'),
        'room1s': [{'address': a} | r for a, r in room1s.items()],
        'room2s': room2s,
        'units': units,
        'unit_errors': errors,
    }


def dump_level(pid, images, capture) -> dict[str, Any]:
    tables = sorted({x['table_address'] for x in capture['unit_table_candidates']})
    if len(tables) != 1:
        raise ValueError('Expected one freshly scanned unit table address')
    token = images['identity']
    if identity(pid) != token:
        raise ValueError('Game process changed before the level dump')
    fd = os.open(f'/proc/{pid}/mem', os.O_RDONLY)
    try:
        reader = ResearchReader(fd, process_mappings(pid), budget=READ_BUDGET)
        result = survey(reader.read, tables[0])
        result['bytes_requested'] = reader.bytes_requested
    finally:
        os.close(fd)
    if identity(pid) != token:
        raise ValueError('Game process changed during the level dump')
    return result
