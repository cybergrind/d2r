"""The route spin of 2026-10-24 12:06 (rca/2026-10-24/route-spin-findings.md; tzloop.py ZONE_LEFT_NO_WAY): an act 1
shard game whose zone turned, the Countess dead, the character back in Black Marsh away from its ways on. The level
run there ends at once and goes to nothing (hunting/choice.py ZONE_LEFT), so each "TZ next level" leg into the
Forgotten Tower moved nothing: the log's cycle (the route's own step took the press, the pickup started the sweep, the
run ended "nothing is left to go to on this level", the next leg cut the sweep's jump) replayed by a way on that posts
that run and moves nobody."""

import re
from dataclasses import replace

import pytest

from inventory_tracking.macros import tzloop
from inventory_tracking.macros.loop import TZ_NEXT_LEVEL
from inventory_tracking.macros.tzroutine import Itinerary
from inventory_tracking.routes.tz_groups import manual_zone
from tests.inventory_tracking.macros.test_tzloop import GAME, Script, rotated_shard_game


BLACK_MARSH, FORGOTTEN_TOWER, HOLE_1 = 6, 20, 11
TOWER = frozenset((20, 21, 22, 23, 24, 25))
HOLE = frozenset((11, 15))


def black_marsh(monkeypatch: pytest.MonkeyPatch, countess_dead: bool = True) -> tuple[Script, list[int]]:
    """The game at 12:06:14: Black Marsh's run made (12:03), its tower and hole not, the act's other levels cleared;
    its legs' way on the live one away from the stairs (running/legs.py `_way_on`: the level run, going nowhere)."""
    monkeypatch.setattr(tzloop, 'MANUAL_TURNED', False)  # the children's way in alone (MANUAL_TURNED finishes them all)
    act1 = manual_zone(1)
    assert act1 is not None
    left = TOWER | HOLE | {BLACK_MARSH}
    game = rotated_shard_game(monkeypatch, frozenset(act1.areas) - left)
    if countess_dead:
        game.killed.add('The Countess')  # 12:05:07 "Boss kill: Countess"
    game.go('waypoint', BLACK_MARSH)  # 12:06:11 "Waypoint to Black Marsh"
    agenda = game.loop.agenda
    agenda.mapped.add(BLACK_MARSH)
    agenda.explored.add(BLACK_MARSH)
    agenda.ran(BLACK_MARSH)
    runs: list[int] = []

    def way_on() -> None:
        # The leg's level run, ended at once by the runner (`_run_over`): the character never moves
        runs.append(game.area)
        agenda.ran(game.area)

    hands = replace(game.hands(), way_on=way_on, at_way=lambda: False, terrorized=lambda area: False)
    game.hands = lambda visit=None: hands  # pyrefly: ignore[bad-assignment]  # every leg the live hands
    return game, runs


def legs_until_blocked(game: Script, child: int, most: int = 200) -> list[str]:
    legs: list[str] = []
    while child not in game.loop.agenda.blocked and len(legs) < most:
        legs.append(game.leg())
    return legs


def test_the_way_into_a_child_of_a_level_the_zone_left_is_blocked_at_its_first_leg(monkeypatch, caplog):
    monkeypatch.setattr(tzloop, 'ZONE_LEFT_NO_WAY', True)
    game, runs = black_marsh(monkeypatch)
    with caplog.at_level('INFO'):
        tower = legs_until_blocked(game, FORGOTTEN_TOWER)
        hole = legs_until_blocked(game, HOLE_1)
    assert tower == [TZ_NEXT_LEVEL]
    assert hole == [TZ_NEXT_LEVEL]
    assert runs == []  # no level run posted: nothing stood still
    why = tzloop.ZONE_LEFT_SAID.format(parent='Black Marsh')
    assert game.loop.agenda.blocked[FORGOTTEN_TOWER] == why
    assert f'Macro: zone: Forgotten Tower (20) blocked: {why}' in caplog.text  # the watch tools' ZONE_BLOCKED words
    assert 'times with no arrival' not in caplog.text
    assert game.area == BLACK_MARSH


def test_without_the_switch_the_legs_spin_until_the_tries_run_out(monkeypatch):
    monkeypatch.setattr(tzloop, 'ZONE_LEFT_NO_WAY', False)
    game, runs = black_marsh(monkeypatch)
    tower = legs_until_blocked(game, FORGOTTEN_TOWER)
    # As live (35 legs, 12:06:14.8-12:06:27.5): WAY_RUNS_A_TRY level runs make a try, WAY_TRIES + 1 tries block it
    assert len(tower) == tzloop.WAY_RUNS_A_TRY * (tzloop.zonenav.WAY_TRIES + 1)
    assert set(tower) == {TZ_NEXT_LEVEL}
    assert len(runs) == len(tower) - 1  # every leg but the blocking one a level run that moved nothing
    assert 'times with no arrival' in game.loop.agenda.blocked[FORGOTTEN_TOWER]


def test_a_child_still_terrorized_or_a_boss_held_is_still_gone_for(monkeypatch):
    monkeypatch.setattr(tzloop, 'ZONE_LEFT_NO_WAY', True)
    game, _ = black_marsh(monkeypatch)
    agenda, plan, hands = game.loop.agenda, game.loop.agenda.plan, game.hands()
    assert tzloop.way_unrun(agenda, plan, BLACK_MARSH, FORGOTTEN_TOWER, hands)
    terror = replace(hands, terrorized=lambda area: area == FORGOTTEN_TOWER)
    assert not tzloop.way_unrun(agenda, plan, BLACK_MARSH, FORGOTTEN_TOWER, terror)  # the child's zone is on
    at_stairs = replace(hands, at_way=lambda: True)
    assert not tzloop.way_unrun(agenda, plan, BLACK_MARSH, FORGOTTEN_TOWER, at_stairs)  # the leg presses through
    still = replace(hands, terrorized=lambda area: True)
    assert not tzloop.way_unrun(agenda, plan, BLACK_MARSH, FORGOTTEN_TOWER, still)  # its run goes to the way
    alive, _ = black_marsh(monkeypatch, countess_dead=False)
    agenda, hands = alive.loop.agenda, alive.hands()
    assert isinstance(agenda.plan, Itinerary)
    tzloop.bosses_planned(agenda, alive.progress, agenda.plan)  # the ledger as a leg plans it
    assert not tzloop.way_unrun(agenda, agenda.plan, BLACK_MARSH, FORGOTTEN_TOWER, hands)  # her run goes on for her


# --- the waypoint back to a shard act's levels read not terrorized (tzloop.py MANUAL_TURNED, 2026-10-24) ---


OTHER_BOSSES = ('Corpsefire', 'Coldcrow', 'Blood Raven', 'Bonebreaker', 'Andariel')  # act 1's, killed before


def played(game: Script, levels: frozenset[int]) -> None:
    """`levels` run and explored before the zone turned, their bosses killed (the game's own record)."""
    agenda = game.loop.agenda
    for level in levels:
        agenda.entered.add(level)
        agenda.mapped.add(level)
        agenda.explored.add(level)
        agenda.ran(level)
    game.killed.update(OTHER_BOSSES)


def after_the_countess(monkeypatch: pytest.MonkeyPatch) -> Script:
    """12:06:10 on 2026-10-24: the town visit over in the Rogue Encampment, the Countess dead, Black Marsh, its tower
    and its hole not played since the zone turned, the act's other levels cleared."""
    act1 = manual_zone(1)
    assert act1 is not None
    others = frozenset(act1.areas) - (TOWER | HOLE | {BLACK_MARSH})
    game = rotated_shard_game(monkeypatch, others)
    played(game, others)
    game.killed.add('The Countess')
    return game


def test_a_shard_acts_levels_read_not_terrorized_are_not_gone_back_to(monkeypatch):
    monkeypatch.setattr(tzloop, 'MANUAL_TURNED', True)
    game = after_the_countess(monkeypatch)
    assert game.leg() != tzloop.TZ_WAYPOINT or game.calls[-1] != ('waypoint', BLACK_MARSH)
    assert ('waypoint', BLACK_MARSH) not in game.calls  # 12:06:11 "Waypoint to Black Marsh" not made
    agenda = game.loop.agenda
    assert agenda.finished >= TOWER | HOLE | {BLACK_MARSH}  # finished by the zone's verdict
    # Done for the game's obligations: no level owed (ACT_OWED), none said blocked or left open at its end, none in the
    # game's record as blocked
    assert not (TOWER | HOLE | {BLACK_MARSH}) & set(tzloop.levels_owed(agenda))
    said = tzloop.blocked_said(agenda) or ''
    assert 'blocked' not in said
    named = {int(word) for word in re.findall(r'\d+', said)}
    assert not named & (TOWER | HOLE | {BLACK_MARSH})  # none left open
    assert not (TOWER | HOLE | {BLACK_MARSH}) & agenda.blocked.keys()


def test_a_boss_alive_there_keeps_her_levels_owed(monkeypatch):
    monkeypatch.setattr(tzloop, 'MANUAL_TURNED', True)
    act1 = manual_zone(1)
    assert act1 is not None
    others = frozenset(act1.areas) - (TOWER | HOLE | {BLACK_MARSH})
    game = rotated_shard_game(monkeypatch, others)
    played(game, others)
    monkeypatch.setattr(tzloop, 'BOSS_STAYS', True)  # the ledger's bosses held (12:03:07: the Countess alive)
    game.leg()
    finished = game.loop.agenda.finished
    assert not (TOWER | {BLACK_MARSH}) & finished  # her way: worked on the way (hunting/choice.py BOSS_ROTATION)
    assert finished >= HOLE  # no boss there


def test_without_manual_turned_the_levels_stay_owed(monkeypatch):
    monkeypatch.setattr(tzloop, 'MANUAL_TURNED', False)
    game = after_the_countess(monkeypatch)
    game.leg()
    assert not (TOWER | HOLE | {BLACK_MARSH}) & game.loop.agenda.finished  # owed: gone back to (ACT_OWED)


# --- The Worldstone Keep Level 2, 13:50:01-13:50:16 on 2026-10-24 (session 20261024T103937Z-a5ddd5d7) ---

HARROGATH, WSK1, WSK2, WSK3 = 109, 128, 129, 130
KEEP = frozenset((128, 129, 130, 131, 132))  # the Keep's levels, the Throne and the Chamber


def worldstone_keep(monkeypatch: pytest.MonkeyPatch) -> tuple[Script, list[int]]:
    """Act 5 played by a shard (13:41:05), Baal killed (13:48:43), the act read not terrorized any more ("The
    Worldstone Keep Level 2 is no longer terrorized: the level run ends", 13:50:01), the character back in Level 2 by
    its waypoint (13:49:56) away from its ways on, the act's other levels played."""
    from inventory_tracking.macros import zonenav
    from inventory_tracking.macros.loop import GameId

    monkeypatch.setattr(zonenav, 'ACTS', frozenset({1, 2, 3, 4, 5}))
    monkeypatch.setattr(tzloop, 'BOSS_STAYS', False)
    act5 = manual_zone(5)
    assert act5 is not None
    game = Script(HARROGATH, monkeypatch, zone=frozenset())
    agenda = game.loop.agenda
    agenda.begin(GameId(GAME, 1))
    game.loop.game_id = GameId(GAME, 1)
    agenda.shard, agenda.acts = 'used', (5,)
    agenda.plan = tzloop.zone_of(game.hands(), agenda.acts, agenda.bosses)
    assert isinstance(agenda.plan, Itinerary)
    tzloop.bosses_planned(agenda, game.progress, agenda.plan)
    game.killed.update(boss.name for boss in agenda.bosses.alive())  # Baal and the act's others dead
    played(game, frozenset(act5.areas) - {WSK1, WSK3, WSK2})
    game.go('waypoint', WSK2)
    agenda.entered.add(WSK2)
    agenda.mapped.add(WSK2)
    agenda.explored.add(WSK2)
    agenda.ran(WSK2)
    runs: list[int] = []

    def way_on() -> None:
        runs.append(game.area)  # the level run of the zone left: over at once, nobody moved
        agenda.ran(game.area)

    hands = replace(game.hands(), way_on=way_on, at_way=lambda: False, terrorized=lambda area: False)
    game.hands = lambda visit=None: hands  # pyrefly: ignore[bad-assignment]  # every leg the live hands
    return game, runs


def test_the_keeps_levels_read_not_terrorized_are_finished_with_no_leg_into_them(monkeypatch):
    monkeypatch.setattr(tzloop, 'MANUAL_TURNED', True)
    monkeypatch.setattr(tzloop, 'ZONE_LEFT_NO_WAY', True)
    game, runs = worldstone_keep(monkeypatch)
    leg = game.leg()
    assert leg != TZ_NEXT_LEVEL  # 13:50:01 "TZ next level" into Level 3 not made: the Keep is done
    assert runs == []
    assert game.loop.agenda.finished >= {WSK1, WSK2, WSK3}
    assert not {WSK1, WSK3} & game.loop.agenda.blocked.keys()  # finished, no block of the game's record


def test_with_zone_left_no_way_alone_each_child_is_blocked_at_its_first_leg(monkeypatch):
    monkeypatch.setattr(tzloop, 'MANUAL_TURNED', False)
    monkeypatch.setattr(tzloop, 'ZONE_LEFT_NO_WAY', True)
    game, runs = worldstone_keep(monkeypatch)
    legs = [game.leg() for _ in range(2)]
    assert legs == [TZ_NEXT_LEVEL, TZ_NEXT_LEVEL]
    assert runs == []
    assert game.loop.agenda.blocked.keys() >= {WSK1, WSK3}


def test_the_keep_spun_until_its_tries_ran_out_with_both_off(monkeypatch):
    monkeypatch.setattr(tzloop, 'MANUAL_TURNED', False)
    monkeypatch.setattr(tzloop, 'ZONE_LEFT_NO_WAY', False)
    game, runs = worldstone_keep(monkeypatch)
    first = legs_until_blocked(game, WSK3)
    second = legs_until_blocked(game, WSK1)
    # As live: ~64 legs in 12 s, Level 3 blocked at 13:50:09.9, Level 1 at 13:50:16, "made 6 times with no arrival"
    assert len(first) + len(second) == 2 * tzloop.WAY_RUNS_A_TRY * (tzloop.zonenav.WAY_TRIES + 1)
    assert 'times with no arrival' in game.loop.agenda.blocked[WSK3]
    assert 'times with no arrival' in game.loop.agenda.blocked[WSK1]
    assert len(runs) == len(first) + len(second) - 2
