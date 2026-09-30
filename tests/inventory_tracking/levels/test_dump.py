"""Win+C request handling: freshness, reporting, failure notification and socket routing."""

import json
import threading

from inventory_tracking.appraisal import service as appraisal_service
from inventory_tracking.levels.dump import LevelDumper
from inventory_tracking.levels.model import Location
from tests.inventory_tracking.levels.fixtures import replay


SUMMARY = {
    'level_no': 74,
    'room2s_in_level': 40,
    'loaded_room1s_in_level': 9,
    'levels_with_room2s': 3,
    'levels_in_act_chain': 20,
    'units': {'monsters': 12},
    'typed_marker_hits': 1,
    'summoner_unit_seen': False,
}


class Source:
    pid, images, capture = 7, {'identity': {'pid': 7}}, {}

    def __init__(self):
        self.connected = 0

    def ensure_connected(self):
        self.connected += 1


def arcane_game_2(pid, images, capture, rooms=False):
    snapshot = replay('arcane_summoner_w')
    return snapshot.location, list(snapshot.rooms) if rooms else []


def dumper(tmp_path, dump, observe=arcane_game_2):
    notes = []
    worker = LevelDumper(
        Source(),
        tmp_path,
        capture_lock=threading.Lock(),
        notify=lambda *a: notes.append(a),
        dump=dump,
        observe=observe,
    )
    return worker, notes


def test_dump_is_published_and_announced(tmp_path):
    worker, notes = dumper(tmp_path, lambda pid, images, capture: {'summary': SUMMARY, 'room2s': []})

    assert worker.request(10.0, 10.2)

    latest = json.loads((tmp_path / 'latest.json').read_text())
    assert latest['state'] == 'complete'
    assert latest['summary'] == SUMMARY
    assert json.loads((tmp_path / latest['run_id'] / 'level.json').read_text())['room2s'] == []
    assert worker.source.connected == 1
    assert notes[0][0] == 'Arcane Sanctuary: ↘ Summoner east'
    assert notes[0][1].startswith('Level 74: 40 Room2s, 9 loaded')


def test_stale_or_repeated_requests_are_ignored(tmp_path):
    worker, notes = dumper(tmp_path, lambda *a: {'summary': SUMMARY})

    assert not worker.request(10.0, 12.0)
    assert worker.request(10.0, 10.1)
    assert not worker.request(10.2, 10.5)
    assert len(notes) == 1


def test_failure_is_reported(tmp_path):
    def fail(*args):
        raise ValueError('No player unit with a room; is a character in game?')

    worker, notes = dumper(tmp_path, fail)

    assert not worker.request(10.0, 10.1)
    assert json.loads((tmp_path / 'latest.json').read_text())['state'] == 'failed'
    assert notes[0][0] == 'Level dump failed'


def test_dispatch_routes_level_requests(tmp_path):
    worker, _ = dumper(tmp_path, lambda *a: {'summary': SUMMARY})

    assert appraisal_service.dispatch(b'level 10.0\n', 10.1, None, None, None, None, worker)
    assert not appraisal_service.dispatch(b'level 10.0', 10.1, None, None, None, None, None)


def test_dump_carries_the_handler_evidence(tmp_path):
    worker, _ = dumper(tmp_path, lambda *a: {'summary': SUMMARY})

    worker.request(10.0, 10.1)

    latest = json.loads((tmp_path / 'latest.json').read_text())
    evidence = json.loads((tmp_path / latest['run_id'] / 'level.json').read_text())['evidence']
    assert (evidence['handler'], evidence['area_id'], len(evidence['rooms'])) == ('Arcane Sanctuary', 74, 61)
    assert evidence['pois'][0]['name'] == 'Act 2 - Arcane Summoner W'
    assert latest['guidance'] == 'Arcane Sanctuary: ↘ Summoner east'


def test_unguided_area_is_named_in_the_notification(tmp_path):
    def town(pid, images, capture, rooms=False):
        return Location(1, 0, 100, 100), []

    worker, notes = dumper(tmp_path, lambda *a: {'summary': SUMMARY}, observe=town)

    worker.request(10.0, 10.1)

    assert notes[0][0] == 'Rogue Encampment: no handler'


def test_confirmed_reader_failure_keeps_the_research_dump(tmp_path):
    def broken(pid, images, capture, rooms=False):
        raise ValueError('Unmapped or unreadable range at 0x18')

    worker, notes = dumper(tmp_path, lambda *a: {'summary': SUMMARY}, observe=broken)

    assert worker.request(10.0, 10.1)
    latest = json.loads((tmp_path / 'latest.json').read_text())
    evidence = json.loads((tmp_path / latest['run_id'] / 'level.json').read_text())['evidence']
    assert evidence == {'error': 'Unmapped or unreadable range at 0x18'}
    assert notes[0][0] == 'Level guidance unavailable'


class Guide:
    def __init__(self, shows):
        self.shows, self.calls = shows, 0

    def press(self, requested_at):
        self.calls += 1
        return self.shows


def test_win_c_shows_the_card_and_dumps_quietly(tmp_path):
    worker, notes = dumper(tmp_path, lambda *a: {'summary': SUMMARY})
    guide = Guide(shows=True)

    assert appraisal_service.dispatch(b'level 10.0', 10.1, None, None, None, None, worker, guide)

    assert guide.calls == 1
    assert json.loads((tmp_path / 'latest.json').read_text())['state'] == 'complete'
    assert notes == []  # the card already says it


def test_win_c_still_announces_when_no_card_could_be_shown(tmp_path):
    worker, notes = dumper(tmp_path, lambda *a: {'summary': SUMMARY})

    assert appraisal_service.dispatch(b'level 10.0', 10.1, None, None, None, None, worker, Guide(shows=False))

    assert notes[0][0] == 'Arcane Sanctuary: ↘ Summoner east'


def test_stale_win_c_neither_shows_nor_dumps(tmp_path):
    worker, _ = dumper(tmp_path, lambda *a: {'summary': SUMMARY})
    guide = Guide(shows=True)

    assert not appraisal_service.dispatch(b'level 10.0', 12.0, None, None, None, None, worker, guide)
    assert guide.calls == 0


def test_headline_says_here_for_the_room_the_player_stands_in(tmp_path):
    def jail_1(pid, images, capture, rooms=False):
        snapshot = replay('jail_1')
        return snapshot.location, list(snapshot.rooms) if rooms else []

    worker, notes = dumper(tmp_path, lambda *a: {'summary': SUMMARY}, observe=jail_1)

    worker.request(10.0, 10.1)

    assert notes[0][0] == 'Jail Level 1: ← Next level west; • Waypoint here; ↗ Barracks north'


def test_notification_names_shrine_candidates_for_checking_in_game():
    from inventory_tracking.levels.dump import describe

    summary = SUMMARY | {'shrine_candidates': [{'txt_id': 2, 'x': 1, 'y': 2, 'type': 18, 'name': 'Gem Shrine'}]}

    _, body = describe(summary)

    assert 'shrines: Gem Shrine' in body
    assert 'shrines' not in describe(SUMMARY)[1]


def test_notification_names_ground_runes_for_checking_positions():
    from inventory_tracking.levels.dump import describe

    items = [{'txt_id': 655, 'mode': 3, 'x': 1, 'y': 2, 'rune': 'Ber Rune'}, {'txt_id': 1, 'mode': 3, 'rune': None}]
    _, body = describe(SUMMARY | {'ground_items': items})

    assert 'ground runes: Ber Rune' in body
    assert 'ground runes' not in describe(SUMMARY)[1]


def test_the_headline_names_the_levels_the_rooms_touch():
    from inventory_tracking.levels.dump import level_evidence
    from inventory_tracking.levels.model import Location, Room

    rooms = [Room(0, 0, 0, 8, 8), Room(5, 8, 0, 8, 8, 3, (8, 0, 8, 8), (4, 17)), Room(6, 16, 0, 8, 8, None, None, (2,))]

    def observe(pid, images, capture, *, rooms=False):
        return Location(1, 0, 20, 20), rooms_read

    rooms_read = rooms
    record, headline = level_evidence(7, {}, {}, observe=observe)

    assert headline == 'Rogue Encampment: no handler; touches Stony Field, Burial Grounds, Blood Moor'
    assert record['rooms'][1] == [5, 8, 0, 8, 8, 3, 8, 0, 8, 8, [4, 17]]
