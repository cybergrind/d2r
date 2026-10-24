"""The room rules' trip for a field item the cube can make no room for (macros/running/recovery.py `_field_trip`,
loot/api.py FIELD_AT_ONCE). The player, 2026-10-20 ~14:58: "we need to optimize space (move to cube) and identify items
during games / if we have no room for optimization to keep picking up items - we need to do town routine"."""

import logging
import threading
from pathlib import Path

import pytest

from inventory_tracking.macros.loop import ANDARIEL, TRIPS_A_GAME, TZ
from inventory_tracking.macros.runner import MacroRunner


GAME = 'cyberg4'
KRISS = 'rare Kriss'


def runner(kind=TZ, *, on: bool = True, carrying: bool = True, area: int | None = 63) -> MacroRunner:
    found = MacroRunner(
        None, capture_lock=threading.Lock(), saved_games=Path('/nonexistent'), display=lambda lines: None,
        place=lambda: (GAME, 63),
    )  # fmt: skip
    found.loop.on, found.loop.kind, found.loop.carrying = on, kind, carrying
    found.loop.seen = (GAME, 0.0)
    found.area_seen = area
    found.attack_mode, found.working = True, True
    return found


def test_a_terror_zone_kind_pushes_the_room_package_and_ends_the_level_run(caplog):
    found = runner()
    with caplog.at_level(logging.INFO):
        assert found._field_trip(KRISS)
    assert found.loop.trips_in(GAME) == 1  # the trip's bookkeeping (tzloop.py `trip`)
    assert found.loop.agenda.package() is not None
    assert not found.attack_mode
    assert found.cancelled.is_set()
    assert found.stand_answered > 0  # watch.py `stood_after_cube` stays the backstop only
    assert "rare Kriss lies on the ground with no room in the inventory or the cube: a trip to town for room (the " \
           "agenda's package)" in caplog.text  # fmt: skip


def test_the_andariel_kind_takes_its_trip_and_back_through_the_portal():
    found = runner(ANDARIEL)
    assert found._field_trip(KRISS)
    assert found.loop.trip_due


@pytest.mark.parametrize(
    ('why', 'changes'),
    [('the loop off', {'on': False}), ('nothing a visit takes away', {'carrying': False})],
)
def test_no_trip_is_made_when_the_room_rules_would_make_none(why, changes):
    found = runner(**changes)
    assert not found._field_trip(KRISS), why
    assert not found.cancelled.is_set(), why
    assert found.attack_mode, why


def test_the_trips_of_a_game_are_bounded():
    found = runner(ANDARIEL)
    for _ in range(TRIPS_A_GAME):
        found.loop.begin_trip(GAME)
    assert not found.loop.may_trip(GAME)
    assert not found._field_trip(KRISS)
    assert not found.loop.trip_due


# --- a stop in a game whose act a Worldstone Shard terrorized (stops.py KEEP, 2026-10-21) ---


def test_a_pickup_stop_with_nothing_valuable_left_keeps_the_game(caplog):
    # Travincal, 13:37:24 on 2026-10-21: a potion no click took; the loop left the game, a shard's act with it
    from inventory_tracking.game.records import HEALING, Drop
    from inventory_tracking.macros.pickup import Missed

    potion = Drop(908541678, 4769.0, 2633.0, 'a super healing potion', HEALING)
    found = runner()
    found.valuable_left = lambda: None
    with caplog.at_level(logging.INFO):
        found._loop_stopped(Missed(potion, 'a super healing potion was under the pointer at 3 aims and no click '
                                                 'picked it up'))  # fmt: skip
    assert not found.loop.abandon
    assert found.loop.on
    assert any('the game is kept (nothing valuable lies on the ground)' in r.message for r in caplog.records)


def test_a_door_stop_in_a_terrorized_game_keeps_it_and_elsewhere_leaves_it(caplog, monkeypatch):
    from dataclasses import replace

    from inventory_tracking.macros import stops
    from inventory_tracking.macros.actuator import Abort

    found = runner(replace(TZ, agenda=True))
    found.valuable_left = lambda: None
    found.loop.agenda.acts = (1,)
    with caplog.at_level(logging.INFO):
        found._loop_stopped(Abort('no click took Crypt', cause='door'))
    assert not found.loop.abandon
    assert any('the game is kept (act 1 terrorized by a shard)' in r.message for r in caplog.records)
    found._loop_stopped(Abort('over 600 s in cyberg4'))  # the watchdog's cap: left all the same
    assert found.loop.abandon
    monkeypatch.setattr(stops, 'TERRORIZED_KEEPS', False)
    left = runner(replace(TZ, agenda=True))
    left.valuable_left = lambda: None
    left.loop.agenda.acts = (1,)
    left._loop_stopped(Abort('no click took Crypt', cause='door'))
    assert left.loop.abandon


# --- a recovery in a game with a boss alive (recovery.py BOSS_RECOVERY, 2026-10-22) ---


WORLDSTONE_KEEP = frozenset((128, 129, 130, 131, 132))  # the zone read terrorized: the Throne, the Chamber


def boss_game(area: int = 131) -> MacroRunner:
    """A zone game whose plan holds Baal (the Worldstone Chamber) and the Throne's waves, none killed: the boss ledger
    on a terror tracker's book (terror/tracker.py), as the service builds it."""
    import time
    from dataclasses import replace

    from inventory_tracking.macros.route import PERFORMED
    from inventory_tracking.macros.tzloop import bosses_planned
    from inventory_tracking.macros.tzroutine import itinerary
    from inventory_tracking.routes.catalog import ROUTES
    from inventory_tracking.routes.progress import Progress
    from inventory_tracking.terror.tracker import ZoneTracker

    found = runner(replace(TZ, agenda=True), area=area)
    found.loop.seen = (GAME, time.monotonic())
    found.valuable_left = lambda: None
    agenda = found.loop.agenda
    agenda.begin(GAME)
    plan = itinerary(WORLDSTONE_KEEP)
    assert plan is not None
    agenda.plan = plan
    bosses_planned(agenda, Progress(ROUTES, PERFORMED, ZoneTracker().killed), plan)
    return found


def test_a_stall_with_a_boss_alive_keeps_the_game_twice_then_stops_the_loop_naming_the_bosses(caplog, monkeypatch):
    # the old any-boss rule (tzloop.py STOPS_FOR_ACT_BOSSES off; the player, 2026-10-23: act bosses only)
    from inventory_tracking.macros import tzloop as _tz

    monkeypatch.setattr(_tz, 'STOPS_FOR_ACT_BOSSES', False)
    # "we need to kill all bosses, no exceptions to that"; recoveries: "yes, should try" (the player, 2026-10-22). The
    # audit: every recovery left the game (rca/2026-10-22/boss-audit-findings.md §4 cause 7)
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.running import recovery

    found = boss_game()
    stall = Abort('the character has not moved for 45 s', cause='stall')
    with caplog.at_level(logging.INFO):
        for _ in range(recovery.BOSS_KEEPS):
            found._loop_stopped(stall)
            assert not found.loop.abandon  # the game kept
            assert found.loop.on
        assert 'this game is kept for Lister the Tormentor (Throne of Destruction)' in caplog.text
        assert '(try 2 of 2): the leg is made again' in caplog.text
        found._loop_stopped(stall)
    assert not found.loop.on  # stopped where it is: no Save and Exit
    assert not found.loop.abandon
    assert 'Baal (The Worldstone Chamber)' in caplog.text
    assert 'tried 2 times for them, the game is not left' in caplog.text
    assert 'the loop stops here for the player' in caplog.text


def test_the_keeps_are_the_books_and_a_restarted_service_counts_on():
    # The tries live in the tracker's file-backed book ('<game-id>-<level>'): a restart does not hand the game more
    from inventory_tracking.macros.running import recovery

    found = boss_game()
    found.loop.agenda.bosses.tried(found.loop.agenda.bosses.alive())
    assert {boss.tries for boss in found.loop.agenda.bosses.alive()} == {1}
    assert recovery.BOSS_KEEPS == 2


def test_beset_with_life_low_leaves_at_once_and_says_the_bosses(caplog, monkeypatch):
    # the old any-boss rule (tzloop.py STOPS_FOR_ACT_BOSSES off; the player, 2026-10-23: act bosses only)
    from inventory_tracking.macros import tzloop as _tz

    monkeypatch.setattr(_tz, 'STOPS_FOR_ACT_BOSSES', False)
    # "we must not die": survival first, never a fight through the danger; the line names what is left alive
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.stops import Beset

    found = boss_game()
    found._beset_facts = lambda game: Beset(low=True)
    with caplog.at_level(logging.INFO):
        found._loop_stopped(Abort('the character is hit standing outside a fight (life 800/2900)', cause='beset'))
    assert found.loop.abandon  # left at once (stops.py LEAVE)
    assert "the game is left for the character's life with Lister the Tormentor (Throne of Destruction)" in caplog.text


def test_beset_otherwise_gets_clear_by_the_town_portal_with_no_fight_and_comes_back_for_the_bosses(caplog):
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.agenda import PORTAL_TO_TOWN, THROUGH_PORTAL
    from inventory_tracking.macros.stops import Beset
    from inventory_tracking.macros.tzloop import DANGER_PORTAL

    found = boss_game()
    found._beset_facts = lambda game: Beset(low=False, again=True)  # the fight back lost, life not low
    with caplog.at_level(logging.INFO):
        found._loop_stopped(Abort('the character is hit standing outside a fight (life 2400/2900)', cause='beset'))
    assert not found.loop.abandon
    top = found.loop.agenda.package()
    assert top is not None
    assert (top.kind, top.label) == (PORTAL_TO_TOWN, DANGER_PORTAL)  # no fight posted for it (tzloop.py `portal_fight`)
    assert any(goal.kind == THROUGH_PORTAL and goal.to == 131 for goal in found.loop.agenda.stack)
    assert found.loop.trips_in(GAME) == 1
    assert 'clear of it by the Town Portal, the town visit, back for' in caplog.text


def test_no_progress_with_a_boss_alive_stops_the_loop_at_once(caplog):
    # 2026-10-22: a game owing a boss is cut by no progress, not by its clock (loop.py NO_PROGRESS_SECONDS)
    from inventory_tracking.macros.actuator import Abort

    found = boss_game()
    found.loop.progressed = (GAME, 0.0, ())  # no progress since the start
    with caplog.at_level(logging.INFO):
        found._loop_stopped(Abort('no progress for 300 s in cyberg4'))
    assert not found.loop.on
    assert not found.loop.abandon
    assert 'no progress for 300 s' in caplog.text


def test_without_a_boss_alive_or_with_the_switch_off_a_recovery_leaves_as_before(monkeypatch):
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.running import recovery

    found = boss_game()
    found.loop.agenda.plan = None  # no zone plan: no boss in scope
    found._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert found.loop.abandon
    monkeypatch.setattr(recovery, 'BOSS_RECOVERY', False)
    off = boss_game()
    off._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert off.loop.abandon
    other = boss_game()
    other.loop.seen = ('another game', other.loop.seen[1] if other.loop.seen else 0.0)
    monkeypatch.setattr(recovery, 'BOSS_RECOVERY', True)
    other._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert other.loop.abandon  # the agenda's plan is another game's: as before


def shard_game(left: str | None = None) -> MacroRunner:
    """A zone game a Worldstone Shard terrorized (act 1), taken up after a restart: no plan read yet."""
    import time
    from dataclasses import replace

    found = runner(replace(TZ, agenda=True))
    found.loop.seen = (GAME, time.monotonic())
    found.valuable_left = lambda: left
    found.loop.agenda.begin(GAME)
    found.loop.agenda.acts = (1,)
    assert found.loop.agenda.plan is None
    return found


def test_a_stall_in_a_shard_game_with_no_plan_read_keeps_it_then_stops_in_place(caplog):
    # The player, 2026-10-23: "make sure that we don't save/exit and waste the shards" (SHARD_HOLDS)
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.running import recovery

    found = shard_game()
    stall = Abort('the character has not moved for 45 s', cause='stall')
    with caplog.at_level(logging.INFO):
        for _ in range(recovery.BOSS_KEEPS):
            found._loop_stopped(stall)
            assert found.loop.on
            assert not found.loop.abandon
        found._loop_stopped(stall)
    assert not found.loop.on
    assert not found.loop.abandon
    assert 'the shard acts [1] not planned yet' in caplog.text


def test_with_shard_holds_off_the_shard_game_with_no_plan_is_left_as_before(monkeypatch):
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.running import recovery

    monkeypatch.setattr(recovery, 'SHARD_HOLDS', False)
    found = shard_game()
    found._loop_stopped(Abort('the character has not moved for 45 s', cause='stall'))
    assert found.loop.abandon


def test_the_fight_back_lost_with_a_valuable_left_gets_clear_by_the_portal_not_a_leave(caplog):
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.agenda import PORTAL_TO_TOWN
    from inventory_tracking.macros.stops import Beset
    from inventory_tracking.macros.tzloop import DANGER_PORTAL

    found = shard_game(left='Unique Grand Charm')
    found.loop.agenda.acts = ()  # no shard: the valuable alone holds the game
    found._beset_facts = lambda game: Beset(low=False, again=True)
    with caplog.at_level(logging.INFO):
        found._loop_stopped(Abort('the character is hit standing outside a fight (life 2400/2900)', cause='beset'))
    assert not found.loop.abandon
    assert found.loop.on
    top = found.loop.agenda.package()
    assert top is not None
    assert (top.kind, top.label) == (PORTAL_TO_TOWN, DANGER_PORTAL)
    assert 'Unique Grand Charm lies on the ground' in caplog.text


def test_beset_with_life_low_in_a_shard_game_still_leaves_at_once():
    # Survival beats the shards: "we must not die or we lose exp and our gear"
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.stops import Beset

    found = shard_game(left='Unique Grand Charm')
    found._beset_facts = lambda game: Beset(low=True)
    found._loop_stopped(Abort('the character is hit standing outside a fight (life 800/2900)', cause='beset'))
    assert found.loop.abandon


def test_an_unplayable_zone_in_a_held_game_stops_the_loop_in_place(caplog):
    from inventory_tracking.macros.actuator import Abort

    found = shard_game()
    with caplog.at_level(logging.INFO):
        found._loop_stopped(Abort('the terror zone Moo Moo Farm is not playable', cause='zone'))
    assert not found.loop.on
    assert not found.loop.abandon
    assert 'the game is not left' in caplog.text
    free = runner()  # no agenda kind, nothing held: left as before
    free._loop_stopped(Abort('the terror zone Moo Moo Farm is not playable', cause='zone'))
    assert free.loop.abandon


def test_a_shard_game_is_cut_by_no_progress_not_by_its_clock(monkeypatch):
    from inventory_tracking.macros.running import watch

    found = shard_game()
    assert watch.game_owes(found, GAME)
    monkeypatch.setattr(watch, 'SHARD_NO_CLOCK', False)
    assert not watch.game_owes(found, GAME)  # no plan: nothing owed read
