"""SHORT_LEVELS (macros/tzroutine.py, agenda.py SHORT; the player, 2026-10-25 ~10:15, on the weak TZ levels: "Shorten
them: clear only the elites, bosses and big packs on those levels, then move on"): the weak areas' policy, the
agenda's targets there, the level done after its run (not owed), and the drops still first."""

import json

import pytest

from inventory_tracking.macros import agenda as agenda_module, tzroutine, zonenav
from inventory_tracking.macros.agenda import (
    BOSS_WAY,
    COVER,
    DROP,
    EXPLORE,
    FULL_CLEAR,
    KILL,
    LEADER_FAR,
    ON_THE_WAY,
    PICKUP,
    PLUS,
    PLUS_WAY,
    SHORT,
    SHORT_PACK,
    TRANSIT,
    Agenda,
    Leader,
    LevelView,
    Objective,
)
from inventory_tracking.macros.tzroutine import itinerary, policy_of, weak_areas
from inventory_tracking.macros.zonenav import LevelState


BURIAL_GROUNDS, COLD_PLAINS, CRYPT, MAUSOLEUM = 17, 3, 18, 19
HERE = (5000.0, 5000.0)
ROOM = ((5300.0, 5300.0), 'an unexplored room')


def pack(first: int, x: float, y: float, size: int, step: float = 6.0) -> tuple[tuple[int, tuple[float, float]], ...]:
    """`size` hostiles from unit `first`, `step` units apart in a row from (x, y): one linked group."""
    return tuple((first + index, (x + index * step, y)) for index in range(size))


def view(**changes) -> LevelView:
    changes.setdefault('frontier', lambda: ROOM)
    changes.setdefault('policy', SHORT)
    return LevelView(BURIAL_GROUNDS, HERE, **changes)


def target(agenda: Agenda, seen: LevelView) -> Objective | None:
    return agenda.in_level(seen)


@pytest.fixture
def agenda() -> Agenda:
    found = Agenda()
    found.begin('cybergg1')
    return found


# --- the weak areas and their policy ----------------------------------------------------------------------------------


def test_the_weak_areas_are_the_data_files_and_the_players_five_are_in_it() -> None:
    rows = json.loads(tzroutine.SHORT_LEVELS_FILE.read_text())
    assert rows['rule']['below_with_travel'] == 1600.0  # the player's "under about 1,600"
    # The five the player was shown (rca/2026-10-25/exp-hour-findings.md): Plains of Despair, Bloody Foothills, Burial
    # Grounds, Blood Moor, Black Marsh
    assert {105, 110, 17, 2, 6} <= weak_areas()
    assert all(row['a_second'] < 1600 for row in rows['levels'])


def test_a_weak_area_is_worked_short_only_with_the_switch_on(monkeypatch) -> None:
    plan = itinerary(frozenset((COLD_PLAINS, BURIAL_GROUNDS, CRYPT, MAUSOLEUM)))
    assert plan is not None
    trip = plan.trip_of(BURIAL_GROUNDS, frozenset())
    assert trip is not None
    assert BURIAL_GROUNDS in trip.zone
    monkeypatch.setattr(tzroutine, 'SHORT_LEVELS', False)
    assert policy_of(BURIAL_GROUNDS, trip) == PLUS  # off: TZ+ as before
    monkeypatch.setattr(tzroutine, 'SHORT_LEVELS', True)
    assert policy_of(BURIAL_GROUNDS, trip) == SHORT
    assert policy_of(CRYPT, trip) == PLUS  # not a weak area
    assert policy_of(BURIAL_GROUNDS, trip, full_clear=True) == FULL_CLEAR  # the Full clear TZ kind is never shortened
    assert policy_of(BURIAL_GROUNDS, None) == TRANSIT  # crossed, off the trip
    # Only TZ+ is shortened: a lighter policy on a weak area stays (SHORT would add the far leaders, or the groups)
    assert policy_of(BURIAL_GROUNDS, trip, plus=False) in (COVER, ON_THE_WAY)
    assert tzroutine.shortened(BURIAL_GROUNDS, PLUS) == SHORT
    for lighter in (ON_THE_WAY, PLUS_WAY, COVER, TRANSIT, BOSS_WAY, FULL_CLEAR):
        assert tzroutine.shortened(BURIAL_GROUNDS, lighter) == lighter
    assert tzroutine.shortened(CRYPT, PLUS) == PLUS


# --- the agenda's targets on a shortened level ------------------------------------------------------------------------


def test_short_takes_a_big_pack_and_leaves_a_small_one_and_the_rooms(agenda: Agenda) -> None:
    small = pack(20, 5020.0, 5000.0, SHORT_PACK - 1)
    big = pack(40, 5000.0, 5040.0, SHORT_PACK)
    found = target(agenda, view(crowd=(*small, *big)))
    assert found is not None
    assert (found.kind, found.unit, found.label) == (KILL, 40, f'a group of {SHORT_PACK}')
    # The small pack only: no room explored, the level is done (the area's end goal)
    assert target(agenda, view(crowd=small)) is None
    # Off (TZ+ on the same level): the small pack is a reasonable group, and the rooms are toured
    plus = target(agenda, view(crowd=small, policy=PLUS))
    assert plus is not None
    assert (plus.kind, plus.unit) == (KILL, 20)
    tour = target(agenda, view(policy=PLUS))
    assert tour is not None
    assert tour.kind == EXPLORE


def test_short_goes_for_every_elite_in_the_read_and_remembered_at_any_distance(agenda: Agenda) -> None:
    far = Leader(60, (5400.0, 5000.0), 'a champion far off')  # beyond WAY_UNITS: a way-on policy leaves it
    found = target(agenda, view(leaders=(far,)))
    assert found is not None
    assert (found.kind, found.unit) == (KILL, 60)
    # Out of the read now, remembered: still gone for, after the near goals, before the level is done
    remembered = Leader(60, (5400.0, 5000.0), 'the remembered monster', live=False)
    again = target(agenda, view(leaders=(remembered,)))
    assert again is not None
    assert (again.kind, again.unit, again.tier) == (KILL, 60, LEADER_FAR)


def test_a_boss_of_the_game_holds_a_shortened_level(agenda: Agenda, monkeypatch) -> None:
    boss = Objective(KILL, 'Blood Raven', agenda_module.LEADER_NEAR, BURIAL_GROUNDS, (5500.0, 5000.0), 77)
    monkeypatch.setattr(Agenda, 'boss_goal', lambda self, seen: boss)
    assert target(agenda, view()) == boss


def test_the_drop_and_its_guards_come_first_on_a_shortened_level(agenda: Agenda) -> None:
    # Hard rule 1 of the d2-loop-watch skill: a valuable in the read is taken, whatever the policy
    drop = Objective(PICKUP, 'Ist Rune', DROP, BURIAL_GROUNDS, (5040.0, 5000.0), 900)
    guard = (11, (5045.0, 5000.0))
    first = target(agenda, view(side=drop, hostiles=(guard,)))
    assert first is not None
    assert (first.kind, first.unit) == (KILL, 11)
    assert target(agenda, view(side=drop)) == drop
    assert target(agenda, view(side=drop, crowd=pack(20, 5020.0, 5000.0, 2))) == drop


def test_the_level_says_its_group_size(agenda: Agenda, caplog) -> None:
    with caplog.at_level('INFO'):
        agenda.worked_as(BURIAL_GROUNDS, SHORT, 92.0)
    assert f'Burial Grounds is worked short (92 hostiles: groups of {SHORT_PACK} and more)' in caplog.text


# --- done, not owed (zone navigation) ---------------------------------------------------------------------------------


def test_a_shortened_level_is_done_after_its_run_and_held_only_by_a_boss_alive() -> None:
    plan = itinerary(frozenset((COLD_PLAINS, BURIAL_GROUNDS, CRYPT, MAUSOLEUM)))
    assert plan is not None
    graph = zonenav.graph_of(plan)
    node = graph.nodes[BURIAL_GROUNDS]
    run_once = LevelState(entered=True, mapped=True, explored=False, runs=1)  # its rooms not all seen
    assert zonenav.fully_explored(node, run_once, SHORT)
    assert not zonenav.fully_explored(node, run_once, PLUS)  # TZ+ tours its rooms first
    assert not zonenav.fully_explored(node, LevelState(entered=True, mapped=True, runs=1, bosses=1), SHORT)
    states = {BURIAL_GROUNDS: run_once, CRYPT: LevelState(entered=True, mapped=True, explored=True, runs=1),
              MAUSOLEUM: LevelState(entered=True, mapped=True, explored=True, runs=1)}  # fmt: skip
    judged = zonenav.judge(graph, states, lambda area, finished: SHORT if area == BURIAL_GROUNDS else PLUS)
    assert BURIAL_GROUNDS in judged.cleared
    assert BURIAL_GROUNDS not in judged.exhausted  # done, not left with rooms unseen


def test_short_never_adds_a_goal_tz_plus_would_skip() -> None:
    # SHORT is TZ+ less the rooms and the small groups: with no room left and no small group the two choose alike, at
    # every look of a level emptied target by target
    leaders = (
        Leader(60, (5400.0, 5000.0), 'a champion far off'),
        Leader(61, (5030.0, 5030.0), 'a unique near'),
        Leader(62, (5900.0, 5900.0), 'the remembered monster', live=False),
    )
    big = pack(40, 5000.0, 5040.0, SHORT_PACK)
    for kept in range(len(leaders) + 1):
        for crowd in (big, ()):
            seen = {'leaders': leaders[:kept], 'crowd': crowd, 'frontier': lambda: None}
            plus, short = Agenda(), Agenda()
            plus.begin('cybergg1')
            short.begin('cybergg1')
            assert short.in_level(view(**seen)) == plus.in_level(view(policy=PLUS, **seen))
