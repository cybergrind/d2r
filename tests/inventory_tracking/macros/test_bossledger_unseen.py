"""The game's bosses owed (macros/bossledger.py BOSS_UNSEEN, tzloop.py `bosses_alive`; rca/2026-10-22/
boss-alive-findings.md): a boss killed is the book's record of it, a boss never seen on a level every room of which was
seen is not there, and neither holds the game's end; a live boss, or one on a level not toured, still does."""

from inventory_tracking.macros import bossledger, tzloop, tzroutine
from inventory_tracking.macros.agenda import Agenda
from inventory_tracking.macros.bossledger import BossLedger
from inventory_tracking.macros.loop import GameId
from inventory_tracking.terror.tracker import ZoneTracker


GAME = GameId('cyberg65', 3054865448)
STONY_TOMB_2, HALLS_3, CLAW_VIPER_2 = 59, 60, 61


def ledger() -> tuple[BossLedger, ZoneTracker]:
    tracker = ZoneTracker(wall=lambda: 1000.0)
    found = BossLedger()
    found.begin(GAME)
    found.attach(tracker.killed)
    return found, tracker


def test_a_boss_never_seen_on_a_level_every_room_of_which_was_seen_is_not_there(caplog):
    found, tracker = ledger()
    found.plan((STONY_TOMB_2, HALLS_3, CLAW_VIPER_2, 131))
    tracker.boss_note(HALLS_3, 'Bloodwitch the Wild', unit=7, seen=True)  # seen by the probe
    with caplog.at_level('INFO'):
        found.unseen((STONY_TOMB_2, HALLS_3, 131))  # toured; the Claw Viper Temple not
    alive = {boss.name for boss in found.alive()}
    assert 'Creeping Feature' not in alive
    assert {'Bloodwitch the Wild', 'Fangskin', 'Colenzo the Annihilator'} <= alive  # seen, not toured, a script's
    (creeping,) = [boss for boss in found.bosses() if boss.name == 'Creeping Feature']
    assert creeping.gone == 'every room of Stony Tomb Level 2 seen and Creeping Feature never seen in this game'
    assert caplog.text.count('Creeping Feature is not where it was looked for') == 1
    found.unseen((STONY_TOMB_2,))
    assert caplog.text.count('Creeping Feature is not where it was looked for') == 1  # said once
    # Seen after all (the probe's sighting, terror/tracker.py BOOK_SIGHT): owed again
    tracker.apply([{'event': 'seen', 'unit_id': 9, 'area': STONY_TOMB_2, 'mode': 1, 'x': 5000, 'y': 5000,
                    'txt_id': 1, 'stats': [], 'data_hex': super_unique(name_id('Creeping Feature'))}])  # fmt: skip
    assert 'Creeping Feature' in {boss.name for boss in found.alive()}


def super_unique(row: int) -> str:
    data = bytearray(0x80)
    data[0x1A] = 0x0A
    data[0x2A:0x2C] = row.to_bytes(2, 'little')
    return data.hex()


def name_id(name: str) -> int:
    from inventory_tracking.terror.elites import table

    return next(row for row, each in table().supers.items() if each == name)


def test_a_kill_in_the_record_is_dead_whatever_the_trackers_state():
    # A kill read back from the probe's logs (terror/tracker.py BOOK_RECALL) is the record's; between a game state's
    # reset and the macros naming the game again the tracker's `killed` is its own state's only
    found, tracker = ledger()
    found.plan((73,))
    tracker.boss_note(73, 'Duriel', killed=True)
    tracker.apply([{'event': 'left_game'}])
    assert tracker.killed() == frozenset()
    assert found.alive() == []


def test_with_the_switch_off_an_unseen_boss_stays_owed(monkeypatch):
    monkeypatch.setattr(bossledger, 'BOSS_UNSEEN', False)
    found, _ = ledger()
    found.plan((STONY_TOMB_2,))
    found.unseen((STONY_TOMB_2,))
    assert [boss.name for boss in found.alive()] == ['Creeping Feature']


def test_the_games_end_is_held_by_a_live_boss_only(monkeypatch):
    # the old any-boss stop (tzloop.py STOPS_FOR_ACT_BOSSES off; the player, 2026-10-23: act bosses only)
    from inventory_tracking.macros import tzloop as _tz

    monkeypatch.setattr(_tz, 'STOPS_FOR_ACT_BOSSES', False)
    # The Worldstone Keep's zone: Baal's kill in the book alone, Lister never seen in a Throne every room of which was
    # seen, the Throne's waves a script's, and an act boss's level is settled by the kill alone
    plan = tzroutine.itinerary(frozenset((128, 129, 130, 131, 132)))
    assert plan is not None
    tracker = ZoneTracker(wall=lambda: 1000.0)
    agenda = Agenda()
    agenda.begin(GAME)
    agenda.bosses.attach(tracker.killed)
    agenda.plan = plan
    agenda.bosses.plan(sorted(tzloop.boss_scope(plan)))
    tracker.boss_note(132, 'Baal', killed=True)
    agenda.explored = {131, 132}
    for name in ('Colenzo the Annihilator', 'Achmel the Cursed', 'Bartuc the Bloody', 'Ventar the Unholy'):
        tracker.boss_note(131, name, killed=True)
    assert tzloop.owed(agenda) is None
    assert tzloop.boss_alive(agenda) is None

    other = Agenda()
    other.begin(GameId('cyberg66', 1))
    other.bosses.attach(tracker.killed)
    other.plan = plan
    other.bosses.plan(sorted(tzloop.boss_scope(plan)))
    other.explored = {131, 132}  # Baal never seen in a toured Chamber: an act boss, still owed
    assert 'Baal (The Worldstone Chamber)' in (tzloop.boss_alive(other) or '')
    assert 'Colenzo the Annihilator' in (tzloop.boss_alive(other) or '')  # a script's: still owed
    assert 'Lister the Tormentor' not in (tzloop.boss_alive(other) or '')
