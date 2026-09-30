"""Evidence from real games, and its conversion into test fixtures.

Every entry into a guided area saves one record under runs/levels/evidence/<area>/. A record is
a fixture (area_id, player, rooms) plus what the handler found (POIs, problems). That makes
confirming a level: play it, then
    uv run --offline python -m inventory_tracking.levels.evidence fixture <record-or-dump> <name>
and write the handler's replay test against tests/inventory_tracking/fixtures/levels/<name>.json.
Win+C dumps convert too: new ones carry an `evidence` section, older ones only the research
survey (Room2 raw blocks), which snapshot_from_research decodes with the confirmed offsets.
"""

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

from inventory_tracking.common import timestamp
from inventory_tracking.levels.model import Guidance, LevelSnapshot, Location, Room
from inventory_tracking.levels.presets import level_name, preset_name
from inventory_tracking.native.layout import (
    PRESET_OBJECT_BOUNDS,
    PRESET_OBJECT_FILE,
    PRESET_RECORD_OBJECT,
    ROOM2_BOUNDS,
    ROOM2_PRESET,
)
from inventory_tracking.reports import publish


DEFAULT_EVIDENCE = Path('inventory_tracking/runs/levels/evidence')
FIXTURES = Path('tests/inventory_tracking/fixtures/levels')
FIXTURE_KEYS = ('area_id', 'player', 'rooms')


def evidence_record(snapshot: LevelSnapshot, handler, guidance: Guidance, *, captured_at=None) -> dict[str, Any]:
    location = snapshot.location
    return {
        'captured_at': captured_at or timestamp(),
        'area_id': location.area_id,
        'level_name': level_name(location.area_id),
        'handler': handler.name,
        'confirmed': handler.confirmed,
        'player': {'x': location.x, 'y': location.y},
        'rooms': [r.row() for r in snapshot.rooms],
        'pois': [
            {'label': p.label, 'kind': p.kind, 'preset': p.room.preset, 'name': preset_name(p.room.preset)}
            for p in guidance.pois
        ],
        'problems': list(guidance.problems),
    }


def fixture(record: dict[str, Any], *, source: str) -> dict[str, Any]:
    return {'source': source, **{key: record[key] for key in FIXTURE_KEYS}}


class EvidenceLog:
    def __init__(self, directory: Path = DEFAULT_EVIDENCE):
        self.directory = directory

    def save(self, record: dict[str, Any]) -> Path:
        folder = self.directory / str(record['area_id'])
        folder.mkdir(parents=True, exist_ok=True)
        stem = re.sub(r'[^0-9T]', '', record['captured_at'])[:15] or 'record'
        path, count = folder / f'{stem}.json', 1
        while path.exists():
            path, count = folder / f'{stem}-{count}.json', count + 1
        publish(path, record)
        return path


def snapshot_from_research(dump: dict[str, Any]) -> LevelSnapshot:
    """Decode an older Win+C level.json (research survey only) with the confirmed Room2 offsets."""
    rooms = []
    for room2 in dump['room2s']:
        blocks = {block['address']: bytes.fromhex(block['hex']) for block in room2['blocks']}
        raw = blocks[room2['address']]
        record = blocks[struct.unpack_from('<Q', raw, ROOM2_PRESET)[0]]
        preset = struct.unpack_from('<I', record)[0]
        variant, block = None, None
        obj = blocks.get(struct.unpack_from('<Q', record, PRESET_RECORD_OBJECT)[0]) if len(record) >= 16 else None
        if obj is not None and len(obj) >= PRESET_OBJECT_BOUNDS + 16 and struct.unpack_from('<I', obj)[0] == preset:
            variant = struct.unpack_from('<I', obj, PRESET_OBJECT_FILE)[0]
            x, y, w, h = struct.unpack_from('<IIII', obj, PRESET_OBJECT_BOUNDS)
            block = (x, y, w, h)
        rooms.append(Room(preset, *struct.unpack_from('<IIII', raw, ROOM2_BOUNDS), variant, block))
    summary = dump['summary']
    location = Location(summary['level_no'], 0, summary['player']['x'], summary['player']['y'])
    return LevelSnapshot(location, tuple(rooms))


def load_fixture_source(path: Path) -> dict[str, Any]:
    """An evidence record, or a Win+C dump (decoded from its research blocks, else its `evidence`)."""
    data = json.loads(path.read_text())
    if all(key in data for key in FIXTURE_KEYS):
        return data
    if not data.get('room2s'):
        return data['evidence']
    # A Win+C dump: its raw Room2 blocks are richer than an `evidence` section an older reader wrote.
    snapshot = snapshot_from_research(data)
    location = snapshot.location
    return {
        'area_id': location.area_id,
        'player': {'x': location.x, 'y': location.y},
        'rooms': [r.row() for r in snapshot.rooms],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('fixture', help='write a test fixture from an evidence record or Win+C dump')
    export.add_argument('source', type=Path)
    export.add_argument('name')
    export.add_argument('--fixtures', type=Path, default=FIXTURES)
    args = parser.parse_args(argv)
    record = load_fixture_source(args.source)
    target = args.fixtures / f'{args.name}.json'
    target.write_text(json.dumps(fixture(record, source=str(args.source)), separators=(',', ':')))
    print(f'{target}: area {record["area_id"]} ({level_name(record["area_id"])}), {len(record["rooms"])} rooms')
    return 0


if __name__ == '__main__':
    sys.exit(main())
