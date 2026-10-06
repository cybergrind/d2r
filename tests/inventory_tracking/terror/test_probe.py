"""Terror Zone probe: kill/visibility events from successive monster snapshots, written as JSONL."""

import json
import threading
from dataclasses import replace

from inventory_tracking.levels.model import Location
from inventory_tracking.terror.bosses import BossTracker
from inventory_tracking.terror.monsters import Monster, MonsterSnapshot
from inventory_tracking.terror.probe import MonsterLedger, TerrorProbe
from inventory_tracking.terror.tracker import ZoneTracker


PLAYER = Location(108, 0x500000, 5000, 5000)


def room(index):
    return (index * 8, 0, 8, 8)


def snapshot(*monsters, location=PLAYER, room2s=(1,), level_rooms=None, complete=True):
    return MonsterSnapshot(location, frozenset(room(r) for r in room2s), level_rooms, tuple(monsters), complete)


def events(ledger, snap, now=1.0):
    return [(e['event'], e.get('unit_id')) for e in ledger.update(snap, now)]


def alive(unit_id, x=5030, y=5040, **extra):
    return Monster(unit_id, 156, 1, x, y, 108, room(1), **extra)


def dead(unit_id, mode=12):
    return Monster(unit_id, 156, mode, 5030, 5040, 108, room(1))


def test_a_kill_is_counted_once_when_a_seen_monster_dies():
    ledger = MonsterLedger()

    first = ledger.update(snapshot(alive(3, data_hex='aa', stats=((0, 6, 1),))), 1.0)
    assert [e['event'] for e in first] == ['area', 'rooms', 'seen']
    assert first[2] | {'t': 0} == {
        'event': 'seen',
        't': 0,
        'unit_id': 3,
        'txt_id': 156,
        'mode': 1,
        'x': 5030,
        'y': 5040,
        'area': 108,
        'distance': 50,
        'data_hex': 'aa',
        'stats': [[0, 6, 1]],
        'room': [8, 0, 8, 8],
    }
    assert events(ledger, snapshot(dead(3, mode=0)), 2.0) == [('died', 3)]
    assert events(ledger, snapshot(dead(3)), 3.0) == []
    assert ledger.killed == {108: 1}


def test_a_corpse_seen_first_is_not_a_kill():
    ledger = MonsterLedger()
    ledger.update(snapshot(), 1.0)

    assert events(ledger, snapshot(dead(4)), 2.0) == [('seen', 4)]
    assert ledger.killed == {}


def test_monsters_left_alive_out_of_range_are_reported_and_come_back():
    ledger = MonsterLedger()
    ledger.update(snapshot(alive(5)), 1.0)

    gone = ledger.update(snapshot(location=Location(108, 0x500000, 6000, 5040)), 2.0)
    assert [(e['event'], e['alive'], e['distance']) for e in gone] == [('gone', True, 970)]
    assert events(ledger, snapshot(alive(5)), 3.0) == [('back', 5)]


def test_an_incomplete_unit_walk_does_not_drop_the_monsters_it_missed():
    ledger = MonsterLedger()
    ledger.update(snapshot(alive(5), alive(6)), 1.0)

    assert events(ledger, snapshot(alive(5), complete=False), 2.0) == []
    assert events(ledger, snapshot(alive(5), alive(6)), 3.0) == []
    assert events(ledger, snapshot(alive(5)), 4.0) == [('gone', 6)]


def test_leaving_the_game_resets_the_ledger():
    ledger = MonsterLedger()
    ledger.update(snapshot(alive(5)), 1.0)
    ledger.update(snapshot(dead(5)), 2.0)

    assert events(ledger, snapshot(location=None), 3.0) == [('left_game', None)]
    assert ledger.killed == {}
    assert ('seen', 5) in events(ledger, snapshot(alive(5)), 4.0)


def test_area_entry_and_newly_loaded_rooms_are_recorded():
    ledger = MonsterLedger()

    entered = ledger.update(snapshot(room2s=(1, 2), level_rooms=40), 1.0)
    assert [(e['event'], e.get('level_rooms'), e.get('new'), e.get('loaded_ever')) for e in entered] == [
        ('area', 40, None, None),
        ('rooms', None, 2, 2),
    ]
    assert events(ledger, snapshot(room2s=(1, 2)), 2.0) == []
    assert [e['loaded_ever'] for e in ledger.update(snapshot(room2s=(2, 3)), 3.0)] == [3]


def test_summary_is_written_periodically():
    ledger = MonsterLedger(summary_seconds=10)
    ledger.update(snapshot(alive(5), alive(6)), 1.0)
    ledger.update(snapshot(dead(5), alive(6)), 5.0)

    summary = [e for e in ledger.update(snapshot(dead(5), alive(6)), 11.5) if e['event'] == 'summary']

    assert summary[0] | {'t': 0} == {
        'event': 'summary',
        't': 0,
        'area': 108,
        'present': 2,
        'alive': 1,
        'seen': 2,
        'killed': 1,
        'rooms_loaded': 1,
        'rooms_loaded_ever': 1,
        'level_rooms': None,
    }


class Source:
    pid, images, capture = 7, {}, {}

    def ensure_connected(self):
        pass


def test_probe_writes_events_and_marks_and_skips_when_the_capture_lock_is_busy(tmp_path):
    lock = threading.Lock()
    calls = []

    def observe(pid, images, capture, *, known, counted_level):
        calls.append((set(known), counted_level))
        return snapshot(alive(5), level_rooms=12 if counted_level != PLAYER.level else None)

    probe = TerrorProbe(Source(), tmp_path / 'terror.jsonl', capture_lock=lock, poll_interval=0.25, observe=observe)
    with lock:
        probe.poll(1.0)
    probe.poll(2.0)
    probe.poll(2.1)  # within the poll interval
    probe.poll(2.5)
    probe.mark(3.0)

    written = [json.loads(line) for line in (tmp_path / 'terror.jsonl').read_text().splitlines()]
    assert [e['event'] for e in written] == ['area', 'rooms', 'seen', 'mark']
    assert written[-1]['present'] == [[5, 156, 1, 5030, 5040]]
    assert calls == [(set(), None), ({5}, PLAYER.level)]


def card_probe(tmp_path, snapshots, *, focused=True, show_unconfirmed=True):
    shown = []

    def observe(pid, images, capture, *, known, counted_level):
        return snapshots.pop(0)

    probe = TerrorProbe(
        Source(),
        tmp_path / 'terror.jsonl',
        capture_lock=threading.Lock(),
        poll_interval=0.25,
        observe=observe,
        tracker=ZoneTracker(),
        display=shown.append,
        focused=lambda images: focused,
        show_unconfirmed=show_unconfirmed,
    )
    return probe, shown


def black_marsh(*monsters):
    return snapshot(*monsters, location=Location(6, 0x500000, 5000, 5000))


def marsh(unit_id, mode=1, **extra):
    return Monster(unit_id, 156, mode, 5030, 5040, 6, room(1), **extra)


def test_the_card_counts_kills_in_the_current_group(tmp_path):
    probe, shown = card_probe(tmp_path, [black_marsh(marsh(5), marsh(6)), black_marsh(marsh(5, 12), marsh(6))])
    probe.poll(1.0)
    probe.poll(2.0)
    probe.tick()

    assert shown[-1][0] == 'Terror · Black Marsh (unconfirmed)'
    assert shown[-1][2] == 'Killed 1 / 199 · 198 left'


def test_a_herald_confirms_the_card_and_unconfirmed_zones_can_be_hidden(tmp_path):
    herald = marsh(9, stats=((0, 367, 1),))
    probe, shown = card_probe(tmp_path, [black_marsh(marsh(5)), black_marsh(marsh(5), herald)], show_unconfirmed=False)
    probe.elites = False
    probe.poll(1.0)
    probe.tick()
    assert shown[-1] == []

    probe.poll(2.0)
    probe.tick()
    assert shown[-1][:3] == [
        'Terror · Black Marsh',
        '↓  Herald T1 alive: south',
        'Next Herald: Tier 2 · T1 seen this game',
    ]


def test_no_card_in_town_or_when_the_game_is_not_focused(tmp_path):
    probe, shown = card_probe(tmp_path, [snapshot(location=Location(1, 0x500000, 5000, 5000))])
    probe.poll(1.0)
    probe.tick()
    assert shown[-1] == []

    unfocused, shown = card_probe(tmp_path, [black_marsh(marsh(5))], focused=False)
    unfocused.poll(1.0)
    unfocused.tick()
    assert shown[-1] == []


def test_research_fields_are_logged_on_first_sight_and_level_entry():
    ledger = MonsterLedger()
    room = (100, 200, 8, 8)
    monster = Monster(3, 156, 1, 5030, 5040, 108, room, base_stats=((0, 12, 95),))

    events = ledger.update(MonsterSnapshot(PLAYER, frozenset({room}), 40, (monster,), True, level_hex='ab'), 1.0)

    by_kind = {e['event']: e for e in events}
    assert by_kind['area']['level_hex'] == 'ab'
    assert by_kind['rooms']['bounds'] == [[100, 200, 8, 8]]
    assert (by_kind['seen']['room'], by_kind['seen']['base_stats']) == ([100, 200, 8, 8], [[0, 12, 95]])


def test_the_card_follows_a_live_herald_with_the_player_position(tmp_path):
    herald = marsh(9, stats=((0, 367, 1),))
    moved = Monster(9, 156, 1, 5000, 4900, 6, room(1))
    probe, shown = card_probe(tmp_path, [black_marsh(herald), black_marsh(moved)])
    probe.poll(1.0)
    probe.tick()
    assert shown[-1][1] == '↓  Herald T1 alive: south'  # (5030, 5040) from the player at (5000, 5000)

    probe.poll(2.0)
    probe.tick()
    assert shown[-1][1] == '↗  Herald T1 alive: north'
    assert probe.tracker.herald_marks(6) == [(1, 5000, 4900)]


def test_boss_kills_of_this_launch_follow_the_terror_lines_and_show_outside_terror_zones_too(tmp_path):
    town = Location(1, 0x500000, 5000, 5000)
    snapshots = [black_marsh(marsh(5)), black_marsh(marsh(5, 12)), snapshot(location=town), snapshot(location=None)]
    probe, shown = card_probe(tmp_path, snapshots)
    probe.bosses = BossTracker(clock=lambda: 50.0)  # marsh() monsters have Andariel's id, 156

    for now in (1.0, 2.0):
        probe.poll(now)
    probe.tick()
    assert shown[-1][0] == 'Terror · Black Marsh (unconfirmed)'
    assert shown[-1][-1] == 'Andariel · 1 kill · last 0:00 ago'

    probe.poll(3.0)
    probe.tick()
    assert shown[-1] == ['Andariel · 1 kill · last 0:00 ago']

    probe.poll(4.0)  # out of the game: nothing to show
    probe.tick()
    assert shown[-1] == []


def test_the_card_gets_the_player_level_read_with_the_monsters(tmp_path):
    forced = 'aa' * 0x1A + '00' + '00' * 5 + '09' + '00' * 0x5F  # plain (+0x1A == 0), modifier 9 at +0x20
    snap = black_marsh(*(marsh(unit_id, data_hex=forced) for unit_id in (5, 6, 7)))
    probe, shown = card_probe(
        tmp_path, [MonsterSnapshot(snap.location, snap.room2s, None, snap.monsters, player_level=93)]
    )
    probe.poll(1.0)
    probe.tick()

    assert shown[-1][:2] == ['Terror · Black Marsh', 'Level 95 · Fire Enchanted']


def test_a_level_whose_struct_could_not_be_read_on_entry_is_read_again(tmp_path):
    # 2026-10-06: stepping into Far Oasis as the service attached, the level read failed once and
    # was never retried, so the game had no seed for that level to be known by.
    level = bytearray(0x400)
    level[0x1E4:0x1EC] = (0xBBBB).to_bytes(8, 'little')
    marsh_now = black_marsh()
    read = MonsterSnapshot(marsh_now.location, marsh_now.room2s, 30, (), level_hex=level.hex())
    counted = []
    snapshots = [marsh_now, read, marsh_now]

    def observe(pid, images, capture, *, known, counted_level):
        counted.append(counted_level)
        return snapshots.pop(0)

    probe, _shown = card_probe(tmp_path, [])
    probe.observe = observe
    for now in (1.0, 2.0, 3.0):
        probe.poll(now)

    assert counted == [None, None, marsh_now.location.level]
    assert probe.tracker.game_levels == {6: (0xBBBB).to_bytes(8, 'little').hex()}
    assert probe.tracker.level_rooms[6] == 30


def test_the_players_life_is_logged_whenever_it_changed():
    ledger = MonsterLedger()

    def life(value, now):
        snap = replace(snapshot(), player_life=value)
        return [(e['life'], e['max']) for e in ledger.update(snap, now) if e['event'] == 'life']

    assert life((900, 1450), 1.0) == [(900, 1450)]
    assert life((900, 1450), 1.25) == []
    assert life((310, 1450), 1.5) == [(310, 1450)]
    assert life(None, 1.75) == []


def test_a_deadly_pack_is_warned_of_on_the_card_outside_terror_zones_too(tmp_path):
    # Eight Dark Rangers (txt id 160) first seen under Fanaticism (stats 350/351), north of the
    # player: up-right on screen.
    aura = ((0, 350, 122), (0, 351, 9))
    archers = [
        Monster(unit_id, 160, 1, 5000 + 2 * unit_id, 4900, 6, room(1), data_hex='00' * 0x80, stats=aura)
        for unit_id in range(8)
    ]
    probe, shown = card_probe(tmp_path, [black_marsh(*archers), black_marsh(*archers)])
    probe.elites = False
    probe.poll(1.0)
    probe.tick()

    # Plain monsters without the zone's forced modifier: not terrorized, so no Terror lines.
    assert shown[-1] == ['↗  ⚠ Dark Ranger x8 · Fanaticism: north']

    probe.danger = False
    probe.poll(2.0)
    probe.tick()
    assert shown[-1] == []


def test_the_card_counts_the_levels_elite_groups_under_the_terror_lines(tmp_path):
    # Black Marsh (6) rolls 7-9 random groups in Hell; the line is there outside Terror Zones too
    # (user, 2026-10-06: on this card, not on the map).
    unique = Monster(50, 160, 1, 5100, 5000, 6, room(1), data_hex='00' * 0x1A + '08' + '00' * 0x65)
    probe, shown = card_probe(tmp_path, [black_marsh(unique), black_marsh()])
    probe.poll(1.0)
    probe.tick()

    assert shown[-1][0].startswith('Terror · Black Marsh')
    assert shown[-1][-1] == 'Elites: 0 killed · 1 alive of 7-9'

    probe.elites = False
    probe.poll(2.0)
    probe.tick()
    assert not any(line.startswith('Elites') for line in shown[-1])
