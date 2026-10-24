"""The terror tracker's boss book as the game's record of its bosses' kills and sightings (terror/tracker.py
BOOK_KILLS, BOOK_FRESH, BOOK_SIGHT, BOOK_RECALL, SEED_JOIN; rca/2026-10-22/boss-alive-findings.md): game cyberg65 had 37
of its 40 bosses killed by 23:15, 24 of them read alive after a restarted service's save dropped the game's
stored state."""

import json
import time
from datetime import UTC, datetime

from inventory_tracking.terror import tracker as tracker_module
from inventory_tracking.terror.tracker import PROBE_LOG, ZoneTracker


GAME = 'cyberg65#3054865448'
DURIEL, LAIR = 211, 73
KAA, KAA_UNIT, TOMB = 19, 1834794757, 67  # Ancient Kaa the Soulless: superuniques.txt row 19, his unit that night


def entered(area, seed):
    """An 'area' event with the level struct the probe reads on entering: its seed is at +0x1E4."""
    level = bytearray(0x400)
    level[0x1E4:0x1EC] = seed.to_bytes(8, 'little')
    return {'event': 'area', 'area': area, 'level_rooms': 30, 'level_hex': level.hex()}


def seen(unit_id, area, x, y, *, txt_id, flags=0x08, super_id=0, mode=1):
    """A monster's first sight: type flags at +0x1A, a super unique's superuniques.txt row at +0x2A."""
    data = bytearray(0x80)
    data[0x1A] = flags
    data[0x2A:0x2C] = super_id.to_bytes(2, 'little')
    return {'event': 'seen', 'unit_id': unit_id, 'area': area, 'mode': mode, 'x': x, 'y': y, 'txt_id': txt_id,
            'stats': [], 'data_hex': data.hex()}  # fmt: skip


def died(unit_id, area, txt_id=0):
    return {'event': 'died', 'unit_id': unit_id, 'area': area, 'txt_id': txt_id}


def herald(unit_id, area):
    data = '00' * 0x18 + '462a0802' + '00' * 0x64  # as the Black Marsh Herald
    return {'event': 'seen', 'unit_id': unit_id, 'area': area, 'mode': 1, 'x': 5100, 'y': 5200,
            'stats': [[0, 367, 3]], 'data_hex': data}  # fmt: skip


def record(tracker, name, area=LAIR):
    return next(rec for level, boss, rec in tracker.boss_book() if (level, boss) == (area, name))


def test_a_stored_part_of_the_game_is_merged_in_and_the_game_is_never_dropped(tmp_path, monkeypatch):
    # 22:06:05: the restarted service rejoined a stored part of cyberg65 holding the Worldstone Chamber's seed alone
    # ("game rejoined; Heralds seen []"), then entered the Keep, whose seed the stored game of acts 1-4 held: its first
    # save dropped that game, Duriel's kill and 30 Heralds with it
    store = tmp_path / 'terror-games.json'
    old = ZoneTracker(store)
    old.apply([entered(1, 0xA1), entered(109, 0xB2), entered(LAIR, 0xC3), herald(9, 6)])
    old.apply([seen(5, LAIR, 22637, 15705, txt_id=DURIEL), died(5, LAIR, DURIEL)])
    old.apply([{'event': 'left_game'}])
    part = ZoneTracker(store)
    part.apply([entered(132, 0xD4)])  # a part of the game, its state empty
    part.save()

    again = ZoneTracker(store)  # the service restarted in the Chamber
    again.apply([entered(132, 0xD4)])
    assert again.restored
    assert again.heralds == []
    assert again.killed() == frozenset()
    again.apply([entered(109, 0xB2)])  # the Keep: a level of the stored game, by its seed
    assert again.killed() == {'Duriel'}
    assert again.heralds == [(3, 'Black Marsh')]
    again.save()
    (game,) = [g for g in json.loads(store.read_text(encoding='utf-8'))['games'] if '1' in g['levels']]
    assert set(game['levels']) == {'1', '109', str(LAIR), '132'}
    assert game['state']['slain'] == ['Duriel']

    monkeypatch.setattr(tracker_module, 'SEED_JOIN', False)  # as before: the stored game dropped by the save
    store.write_text(json.dumps({'games': json.loads(store.read_text(encoding='utf-8'))['games'][:0]}))
    old = ZoneTracker(store)
    old.apply([entered(1, 0xA1), entered(109, 0xB2), seen(5, LAIR, 1, 1, txt_id=DURIEL), died(5, LAIR, DURIEL)])
    old.save()
    part = ZoneTracker(store)
    part.apply([entered(132, 0xD4)])
    part.save()
    lost = ZoneTracker(store)
    lost.apply([entered(132, 0xD4), entered(109, 0xB2)])
    lost.save()
    assert lost.killed() == frozenset()
    assert all(game['state']['slain'] == [] for game in json.loads(store.read_text(encoding='utf-8'))['games'])


def test_the_probe_writes_into_the_book_only_of_the_game_named_for_its_state():
    # After a game change the book's game was the old one until the agenda began the new one (a KP_1 run with the loop
    # off never does): the new game's kills went into the old game's book, and the old game's kills were the new one's
    tracker = ZoneTracker(wall=lambda: 1000.0)
    tracker.boss_game('old#1')
    assert tracker.boss_note(37, 'Andariel', by='route')
    tracker.apply([seen(5, 37, 22556, 9556, txt_id=156), died(5, 37, 156)])
    assert tracker.killed() == {'Andariel'}
    tracker.apply([{'event': 'left_game'}])  # the game left: the old game's book is no longer this state's
    assert tracker.killed() == frozenset()
    tracker.apply([seen(6, 37, 22556, 9556, txt_id=156), died(6, 37, 156)])  # the new game's Andariel
    assert tracker.killed() == {'Andariel'}  # the state's own
    tracker.boss_game('new#2')
    assert [name for _, name, rec in tracker.boss_book() if rec.get('killed')] == []  # read back by `recall` only
    tracker.boss_game('old#1')
    assert [rec.get('killed') for _, _, rec in tracker.boss_book()] == [True]  # the old game's one kill, its own


def test_a_boss_seen_by_the_probe_is_seen_in_the_book_and_a_super_uniques_corpse_is_its_kill():
    # A route's boss has no spot of its own: the ledger's binding near a spot never took Duriel, the Countess, Radament
    tracker = ZoneTracker(wall=lambda: 1000.0)
    tracker.boss_game(GAME)
    tracker.boss_note(LAIR, 'Duriel', by='route')
    tracker.boss_note(TOMB, 'Ancient Kaa the Soulless', place=(22685.0, 6891.0), by='rooms')
    tracker.apply([seen(5, LAIR, 22637, 15705, txt_id=DURIEL)])
    duriel = record(tracker, 'Duriel')
    assert (duriel['seen'], duriel['unit'], duriel['place'], duriel.get('killed')) == (
        True,
        5,
        [22637.0, 15705.0],
        None,
    )
    tracker.apply([seen(7, 40, 5000, 5000, txt_id=DURIEL)])  # no record of him there: none made
    assert {(level, name) for level, name, _ in tracker.boss_book()} == {
        (LAIR, 'Duriel'),
        (TOMB, 'Ancient Kaa the Soulless'),
    }
    # Kaa's corpse first seen by a restarted service: killed this game
    tracker.apply([seen(KAA_UNIT, TOMB, 22691, 6887, txt_id=103, flags=0x0A, super_id=KAA, mode=12)])
    assert record(tracker, 'Ancient Kaa the Soulless', TOMB)['killed'] is True
    assert 'Ancient Kaa the Soulless' in tracker.killed()


def test_the_death_of_a_unit_the_ledger_took_for_a_boss_is_its_kill():
    tracker = ZoneTracker(wall=lambda: 1000.0)
    tracker.boss_game(GAME)
    tracker.boss_note(TOMB, 'Ancient Kaa the Soulless', place=(22685.0, 6891.0), unit=KAA_UNIT, seen=True, by='rooms')
    tracker.apply([died(KAA_UNIT, TOMB, 103)])  # first seen without its name (no super unique row read)
    assert record(tracker, 'Ancient Kaa the Soulless', TOMB)['killed'] is True
    tracker.apply([died(42, TOMB, 103)])  # any other unit: nothing
    assert [name for _, name, rec in tracker.boss_book() if rec.get('killed')] == ['Ancient Kaa the Soulless']


def probe_log(folder, events):
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / PROBE_LOG
    with log.open('a', encoding='utf-8') as file:
        for at, event in events:
            stamp = datetime.fromtimestamp(at, UTC).isoformat()
            file.write(json.dumps({'at': stamp, **event}, separators=(',', ':')) + '\n')
    return log


def test_the_probe_logs_of_the_game_since_it_began_are_read_into_its_book_when_it_is_named(tmp_path, caplog):
    # The live record of cyberg65: Duriel killed at 19:59:56, the kill lost with the game state at 22:06; the next
    # service read the book with his record unkilled and the loop went back to his Lair (23:12:40)
    store = tmp_path / 'terror-games.json'
    began = time.time() - 600
    before = ZoneTracker(store)
    before.boss_game(GAME)
    before.boss_note(LAIR, 'Duriel', by='route')
    before.boss_note(TOMB, 'Ancient Kaa the Soulless', place=(22685.0, 6891.0), by='rooms')
    before.boss_note(37, 'Andariel', by='route')
    before.record_note(GAME, 'loop', {'began': began})
    session = tmp_path / '20261022T164938Z-2f4f5df0'
    log = probe_log(session, [
        (began - 60, {**seen(1, 37, 22556, 9556, txt_id=156)}),  # the game before this one: not this game's
        (began - 59, died(1, 37, 156)),
        (began + 10, seen(5, LAIR, 22637, 15705, txt_id=DURIEL)),
        (began + 20, died(5, LAIR, DURIEL)),
        (began + 30, seen(KAA_UNIT, TOMB, 22691, 6887, txt_id=103, flags=0x0A, super_id=KAA)),
    ])  # fmt: skip

    again = ZoneTracker(store)  # the service restarted: the book read back, Duriel's kill not in it
    with caplog.at_level('INFO'):
        again.boss_game(GAME)
    assert again.killed() == {'Duriel'}
    assert record(again, 'Ancient Kaa the Soulless', TOMB)['seen'] is True
    assert not record(again, 'Andariel', 37).get('killed')
    assert "the probe's logs of game cyberg65#3054865448" in caplog.text
    held = json.loads(store.read_text(encoding='utf-8'))['bosses']
    assert held[f'{GAME}-{LAIR}']['Duriel']['killed'] is True  # in the file: the next service reads it there

    # Read on from where it stopped, a line being written read once whole
    with log.open('a', encoding='utf-8') as file:
        file.write(json.dumps({'at': datetime.fromtimestamp(began + 40, UTC).isoformat(), **died(KAA_UNIT, TOMB, 103)}))
    again.apply([{'event': 'left_game'}])
    again.boss_game(GAME)
    assert 'Ancient Kaa the Soulless' not in again.killed()
    with log.open('a', encoding='utf-8') as file:
        file.write('\n')
    again.apply([{'event': 'left_game'}])
    again.boss_game(GAME)
    assert again.killed() == {'Duriel', 'Ancient Kaa the Soulless'}


def test_without_the_games_record_or_with_the_switch_off_nothing_is_read(tmp_path, monkeypatch):
    store = tmp_path / 'terror-games.json'
    began = time.time() - 600
    first = ZoneTracker(store)
    first.boss_game(GAME)
    first.boss_note(LAIR, 'Duriel', by='route')
    probe_log(
        tmp_path / 'session', [(began + 10, seen(5, LAIR, 1, 1, txt_id=DURIEL)), (began + 20, died(5, LAIR, DURIEL))]
    )
    unrecorded = ZoneTracker(store)
    unrecorded.boss_game(GAME)  # no record of the game: when it began is not known
    assert unrecorded.killed() == frozenset()
    first.record_note(GAME, 'loop', {'began': began})
    monkeypatch.setattr(tracker_module, 'BOOK_RECALL', False)
    off = ZoneTracker(store)
    off.boss_game(GAME)
    assert off.killed() == frozenset()
