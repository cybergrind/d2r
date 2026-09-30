"""Evidence records double as test fixtures; old Win+C research dumps convert to the same shape."""

import json
import struct

from inventory_tracking.levels.evidence import EvidenceLog, evidence_record, fixture, snapshot_from_research
from inventory_tracking.levels.registry import handler_for
from tests.inventory_tracking.levels.fixtures import FIXTURES, replay


def test_record_carries_the_fixture_fields_and_what_the_handler_found():
    snapshot = replay('arcane_summoner_w')
    handler = handler_for(74)

    record = evidence_record(snapshot, handler, handler.guide(snapshot), captured_at='2026-09-30T00:00:00+00:00')

    assert record['area_id'] == 74
    assert record['level_name'] == 'Arcane Sanctuary'
    assert (record['handler'], record['confirmed']) == ('Arcane Sanctuary', True)
    assert record['player'] == {'x': snapshot.location.x, 'y': snapshot.location.y}
    assert len(record['rooms']) == 61
    assert record['pois'] == [
        {'label': 'Summoner', 'kind': 'target', 'preset': 525, 'name': 'Act 2 - Arcane Summoner W'}
    ]
    assert record['problems'] == []


def test_fixture_from_evidence_round_trips_through_replay(tmp_path):
    snapshot = replay('arcane_summoner_s')
    handler = handler_for(74)
    record = evidence_record(snapshot, handler, handler.guide(snapshot), captured_at='t')

    data = fixture(record, source='evidence test')

    assert set(data) == {'source', 'area_id', 'player', 'rooms'}
    assert data['rooms'] == json.loads((FIXTURES / 'arcane_summoner_s.json').read_text())['rooms']


def test_evidence_log_writes_one_file_per_record_under_its_area(tmp_path):
    log = EvidenceLog(tmp_path)

    first = log.save({'area_id': 74, 'captured_at': '2026-09-30T06:20:28.1+00:00'})
    second = log.save({'area_id': 74, 'captured_at': '2026-09-30T06:22:20.2+00:00'})

    assert first.parent == second.parent == tmp_path / '74'
    assert first != second
    assert json.loads(second.read_text())['captured_at'].startswith('2026-09-30T06:22')


def research_dump(level, rooms, objects=None):
    """The Win+C research shape: Room2 raw block, its +0x40 preset record and (optional) preset object."""
    room2s = []
    for index, (preset, x, y, width, height) in enumerate(rooms):
        address, preset_address = 0x310000 + index * 0x200, 0x320000 + index * 0x100
        raw = bytearray(0x100)
        struct.pack_into('<Q', raw, 0x40, preset_address)
        struct.pack_into('<IIII', raw, 0x60, x, y, width, height)
        blocks = [{'address': address, 'hex': raw.hex()}]
        record = bytearray(0x80)
        struct.pack_into('<I', record, 0, preset)
        if objects and index in objects:
            variant, bounds = objects[index]
            object_address = 0x330000 + index * 0x100
            struct.pack_into('<Q', record, 8, object_address)
            obj = bytearray(0x80)
            struct.pack_into('<II', obj, 0, preset, variant)
            struct.pack_into('<IIII', obj, 0x18, *bounds)
            blocks.append({'address': object_address, 'hex': obj.hex()})
        blocks.append({'address': preset_address, 'hex': record.hex()})
        room2s.append({'address': address, 'blocks': blocks})
    return {'summary': {'level_no': level, 'player': {'x': 25450, 'y': 5442}}, 'room2s': room2s}


def test_old_research_dump_converts_to_a_snapshot():
    dump = research_dump(74, [(524, 5084, 1084, 12, 12), (527, 5084, 1000, 12, 12)])

    snapshot = snapshot_from_research(dump)

    assert snapshot.location.area_id == 74
    assert (snapshot.location.x, snapshot.location.y) == (25450, 5442)
    assert [(r.preset, r.x, r.y) for r in snapshot.rooms] == [(524, 5084, 1084), (527, 5084, 1000)]


def test_research_dump_decodes_preset_variant_and_bounds():
    dump = research_dump(124, [(864, 2500, 1000, 8, 8), (864, 2508, 1000, 8, 8)], {0: (3, (2500, 1000, 84, 84))})

    first, second = snapshot_from_research(dump).rooms

    assert (first.variant, first.block) == (3, (2500, 1000, 84, 84))
    assert (second.variant, second.block) == (None, None)


def test_rooms_with_a_preset_object_keep_it_through_record_and_replay():
    from inventory_tracking.levels.model import LevelSnapshot, Location, Room

    room = Room(864, 2500, 1000, 8, 8, 3, (2500, 1000, 84, 84))
    snapshot = LevelSnapshot(Location(124, 0, 12720, 5236), (room, Room(1, 0, 0, 8, 8)))
    handler = handler_for(124)
    record = evidence_record(snapshot, handler, handler.guide(snapshot), captured_at='t')

    assert record['rooms'] == [[864, 2500, 1000, 8, 8, 3, 2500, 1000, 84, 84], [1, 0, 0, 8, 8]]
