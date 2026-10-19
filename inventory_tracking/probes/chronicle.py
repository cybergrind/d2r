"""Host-only read of the character's Chronicle: uv run -m inventory_tracking.probes.chronicle.

The Chronicle (the uniques, set items and runewords this account has found) is not in the save folder; the
client keeps it on the player's data record as three hash maps, one per kind (client code 2026-10-11:
sub_140278400 adds an entry, sub_1402d72f0 looks one up). Run it in a game, as the character.

A map is {bucket count, bucket array, entry count, load factor}; a bucket is a chain of nodes
{next, id, id, kind, ?, found}. The id is the row of the kind's table; found is minutes since 1970 (the
first dump, 2026-10-11, spans 2026-02-14 to that day); the 16-bit field is kept raw (the panel has a
"dropped by" line, not checked against it).
"""

import argparse
import json
import struct
from pathlib import Path
from typing import Any

from inventory_tracking.game.decode import local_player
from inventory_tracking.game.memory import GameMemory
from inventory_tracking.items.metadata import metadata
from inventory_tracking.native.process import find_game_processes
from inventory_tracking.native.units import walk_units
from inventory_tracking.reports import publish


BASE = 0x140000000
TABLE_CACHE = Path('inventory_tracking/runs/osd/unit-table.json')
OUTPUT = Path('inventory_tracking/runs/chronicle/chronicle.json')
MAPS = 0x220  # in the player's data record
MAP_SIZE = 0x20
KINDS = ('set', 'unique', 'runeword')  # the order of the maps; the kind byte of an entry (dump of 2026-10-11)
NODE = struct.Struct('<QiiBxHI')
MOST_BUCKETS = 1 << 16
MOST_ENTRIES = 4096


def entries(read, data_pointer: int) -> dict[str, list[dict[str, Any]]]:
    """Kind -> the Chronicle's entries of that kind, read from the player's data record."""
    found: dict[str, list[dict[str, Any]]] = {}
    for index, kind in enumerate(KINDS):
        buckets, array, count, _ = struct.unpack('<QQQQ', read(data_pointer + MAPS + index * MAP_SIZE, MAP_SIZE))
        rows: list[dict[str, Any]] = []
        if array and 0 < buckets <= MOST_BUCKETS:
            for head in struct.unpack(f'<{buckets}Q', read(array, buckets * 8)):
                while head and len(rows) < MOST_ENTRIES:
                    head, row, _, byte, word, minutes = NODE.unpack(read(head, NODE.size))
                    rows.append({'id': row, 'kind': byte, 'word': word, 'found': minutes * 60})
        if len(rows) != count:
            raise ValueError(f'{kind}: the map says {count} entries, {len(rows)} read')
        found[kind] = sorted(rows, key=lambda entry: entry['id'])
    return found


def names(kind: str) -> dict[int, str]:
    """Table row -> item name, for the kinds the item metadata numbers the way the game does."""
    if kind == 'runeword':
        return {}
    return {row['game_definition']['*ID']: row['name'] for row in metadata()['identities'][kind].values()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    table = BASE + next(iter(json.loads(TABLE_CACHE.read_text()).values()))['table_rva']
    games = find_game_processes()
    if not games:
        raise SystemExit('the game is not running, or this shell cannot see it: run it from a terminal of your own')
    memory = GameMemory(games[0], BASE, table)
    try:
        player = local_player(memory.read, table)
        if player is None:
            raise SystemExit('no character: run it in a game')
        heads = struct.unpack('<128Q', memory.read(table, 1024))
        unit = next(u for u in walk_units(memory.read, heads, 0)['units'] if u['unit_id'] == player.unit_id)
        found = entries(memory.read, unit['data_pointer'])
    finally:
        memory.close()
    for kind, rows in found.items():
        known = names(kind)
        for row in rows:
            row['name'] = known.get(row['id'])
        print(kind, len(rows))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    publish(args.output, {'character': player.name, 'entries': found})
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
