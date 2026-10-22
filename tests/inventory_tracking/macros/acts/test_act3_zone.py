"""Act 3 played by zone navigation (macros/zonenav.py, stage 1 of macros/zone-nav-plan.md): each waypoint taken once
(the Flayer Jungle twice, for its two deep chains), the temples left by their way back, a deep chain ended by the Town
Portal, and the cases that must not stop the zone: a map never read, a door no click takes, a way back that fails, a
room trip in a child, the game given up."""

import logging

import pytest

from inventory_tracking.macros import tzloop, zonenav
from inventory_tracking.macros.agenda import PLUS, LevelView
from inventory_tracking.macros.loop import LEAVE, TOWN, TZ_BACK, TZ_PORTAL, TZ_UP, TZ_WAYPOINT
from inventory_tracking.macros.town import Exit
from inventory_tracking.routes.model import ENTER
from tests.inventory_tracking.macros.acts.harness import ActGame, crossing


KURAST_DOCKS, FORTRESS = 75, 103
ACT_3 = (
    *(101, 102, 83, 100, 81, 82, 98, 99, 96, 97, 80, 92, 93, 94, 95),
    *(79, 78, 88, 89, 91, 86, 87, 90, 77, 76, 84, 85),
)


@pytest.fixture
def zone(monkeypatch):
    monkeypatch.setattr(zonenav, 'ACTS', frozenset((3,)))


def act_3(monkeypatch) -> ActGame:
    return ActGame(3, monkeypatch, rotation=frozenset())


def between(moves, first, then):
    """Whether `then` comes right after `first` among the moves."""
    return any(moves[index : index + 2] == [first, then] for index in range(len(moves) - 1))


@pytest.mark.usefixtures('zone')
def test_act_3_takes_each_waypoint_once_and_climbs_out_of_the_temples(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    walk = act_3(monkeypatch).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    # was 15 waypoint trips (the act's plan, 08:57:43 on 2026-10-21): Upper Kurast 4 times, the Bazaar 3 times
    assert walk.waypoints == [101, 83, 81, 80, 79, 78, 78, 77, 76, FORTRESS]
    for temple, city in ((96, 81), (97, 81), (98, 82), (94, 80), (95, 80), (84, 76)):
        assert between(walk.moves, ('door', temple), ('door', city)), temple  # its way back, no Town Portal
    assert between(walk.moves, ('door', 93), ('portal', KURAST_DOCKS))  # the Sewers last in the Bazaar: the portal
    assert between(walk.moves, ('door', 91), ('portal', KURAST_DOCKS))  # the first jungle chain: the portal
    entered = {area for _, area in walk.moves}
    assert set(ACT_3) <= entered
    assert walk.kills == [
        'Mephisto',
        'Ismail Vilehand',
        'Battlemaid Sarina',
        'Witch Doctor Endugu',
        'Sszark the Burning',
    ]
    assert walk.legs.count(TZ_UP) == 6  # out of 96, 97, 98, 94, 95, 84
    said = caplog.text
    assert 'Macro: zone: graph Act3-Manual: 101 (102); 83 (100); 81 (82 (98, 99), 96, 97)' in said
    assert 'Macro: zone: Upper Kurast (81) explored, held by [82]' in said
    assert 'Macro: zone: Upper Kurast (81) cleared' in said


@pytest.mark.usefixtures('zone')
def test_a_temple_whose_map_is_never_read_is_run_again_then_blocked_and_the_city_goes_on(monkeypatch, caplog):
    # The Forgotten Reliquary (28 hostiles) was "done" 0.2 s after arrival, no map read (09:09:02 on 2026-10-21)
    caplog.set_level(logging.INFO)
    game = act_3(monkeypatch)
    game.game.unmapped = {96}
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.runs.count(96) == zonenav.MAP_TRIES
    assert 'Macro: zone: Forgotten Reliquary (96) blocked: its map was never read in 2 runs' in caplog.text
    assert between(walk.moves, ('door', 96), ('door', 81))  # its way back all the same
    assert ('door', 97) in walk.moves
    assert 'Upper Kurast (81) cleared, without [96]' in caplog.text


@pytest.mark.usefixtures('zone')
def test_a_door_no_click_takes_blocks_its_child_and_the_parent_goes_on(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    game = act_3(monkeypatch)
    game.game.stuck = {97}
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert ('door', 97) not in walk.moves
    assert 'Macro: zone: no click took Forgotten Temple: Forgotten Temple blocked, Upper Kurast goes on' in caplog.text
    assert ('door', 82) in walk.moves  # the Causeway after it
    assert walk.waypoints.count(81) == 1


@pytest.mark.usefixtures('zone')
def test_a_way_back_that_takes_no_click_is_the_town_portal_and_the_waypoint_back(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    game = act_3(monkeypatch)
    game.game.stuck = {81}  # every door into Upper Kurast: the temples' ways back
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert between(walk.moves, ('door', 96), ('portal', KURAST_DOCKS))
    assert 'no way back up from Forgotten Reliquary: the Town Portal instead' in caplog.text
    assert walk.waypoints.count(81) == 3  # the city's own, back after each temple
    assert ('door', 97) in walk.moves


@pytest.mark.usefixtures('zone')
def test_a_room_trip_in_a_temple_comes_back_through_the_portal_into_it(monkeypatch):
    game = act_3(monkeypatch)
    exits: list[Exit] = []

    def run_of(area: int) -> None:
        if area == 96 and not exits:
            tzloop.trip(game.game.loop, game.game.play.world.game_name, area)  # no room for a valuable

    game.on_run = run_of
    walk = game.play(visit=exits.append)

    assert walk.stopped is None, (walk.stopped, walk.where)
    trip = walk.legs.index(TOWN) - 2
    assert walk.legs[trip : trip + 5] == [TZ_PORTAL, TZ_WAYPOINT, TOWN, TZ_WAYPOINT, TZ_BACK]
    assert ('through', 96) in walk.moves
    assert between(walk.moves, ('through', 96), ('door', 81))  # then its way back, as before the trip
    assert exits == [Exit.PORTAL]


@pytest.mark.usefixtures('zone')
def test_a_game_given_up_mid_zone_is_left_at_once(monkeypatch):
    # The watchdog's cap (loop.py ACT_SECONDS) and a recovery give the game up (`Loop.abandon`): no zone goal after it
    game = act_3(monkeypatch)

    def run_of(area: int) -> None:
        if area == 97:
            game.game.loop.abandon = True

    game.on_run = run_of
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert walk.legs[-1] == LEAVE
    assert walk.runs[-1] == 97


def test_with_the_switch_off_act_3_plays_its_fifteen_trips_as_before(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    walk = act_3(monkeypatch).play()

    assert walk.waypoints.count(81) == 4
    assert TZ_UP not in walk.legs
    assert 'Macro: zone: graph Act3-Manual' in caplog.text  # stage 0: the graph and the old rule's verdicts said
    assert 'Macro: zone: done by the old rule: Forgotten Reliquary (96) cleared' in caplog.text


def passing_game(monkeypatch) -> tuple[ActGame, list[tuple[int, bool]]]:
    """An Act 3 game whose Upper Kurast runs ask the agenda as the live run does (hunting/choice.py `agenda_target`):
    a room ahead at 100 units, the route stage's door at 40 (`zonenav.enter_at` its `use_at`). A run the agenda sends to
    the door first ends there, its rooms not all seen (`cut_short`). Records, at each temple's first run, whether Upper
    Kurast was explored by then."""
    game = act_3(monkeypatch)
    seen: list[tuple[int, bool]] = []
    here, door, room = (5000.0, 5000.0), (5040.0, 5000.0), ((5100.0, 5000.0), 'an unexplored room')

    def run_of(area: int) -> None:
        agenda = game.game.loop.agenda
        if area in (96, 97) and area not in [level for level, _ in seen]:
            seen.append((area, UPPER_KURAST in agenda.explored))
        if area != UPPER_KURAST:
            return
        step = game.game.progress.step(area)
        use_at = zonenav.enter_at(agenda.plan, step.stage, door) if step is not None else None
        target = agenda.in_level(LevelView(area, here, frontier=lambda: room, policy=PLUS, use_at=use_at))
        if target is None:
            game.game.cut_short.add(area)  # the run went to the door beside it: in, before the rooms

    game.on_run = run_of
    return game, seen


UPPER_KURAST = 81


@pytest.mark.usefixtures('zone')
def test_a_temple_passed_is_gone_into_first_climbed_out_of_then_the_city_is_finished(monkeypatch):
    game, seen = passing_game(monkeypatch)
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert seen == [(96, False), (97, False)]  # each temple as the city's run passed it, the city's rooms after
    city = [index for index, area in enumerate(walk.runs) if area == UPPER_KURAST]
    assert len(city) == 3  # to the Reliquary's door, to the Temple's door, then the rest of its rooms
    assert walk.runs[city[0] + 1] == 96
    assert walk.runs[city[1] + 1] == 97
    assert between(walk.moves, ('door', 96), ('door', UPPER_KURAST))
    assert between(walk.moves, ('door', 97), ('door', UPPER_KURAST))
    assert walk.moves.index(('door', 82)) > walk.moves.index(('door', 97))  # the Causeway (deep) once it is explored


@pytest.mark.usefixtures('zone')
def test_with_enter_passing_off_the_city_is_explored_before_its_temples(monkeypatch):
    monkeypatch.setattr(zonenav, 'ENTER_PASSING', False)
    game, seen = passing_game(monkeypatch)
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert seen == [(96, True), (97, True)]


def passage_game(monkeypatch) -> ActGame:
    return crossing(act_3(monkeypatch))


@pytest.mark.usefixtures('zone')
def test_the_causeway_is_walked_into_from_upper_kurast_and_back_across_its_open_passage(monkeypatch):
    walk = passage_game(monkeypatch).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    # 13:48:00 on 2026-10-21: "Kurast Causeway leads off the trip" 30 times, then the repeat guard left the game
    assert between(walk.moves, ('door', 81), ('walk', 82))  # after the Forgotten Temple, across the passage
    assert {82, 98, 99} <= set(walk.levels)
    assert walk.waypoints.count(81) == 1


@pytest.mark.usefixtures('zone')
def test_a_passage_never_crossed_blocks_its_child_and_the_zone_goes_on(monkeypatch, caplog):
    # A run that may never cross (its own level only, the bug's `allowed`): the Causeway is blocked after WAY_TRIES
    # legs, said, and the zone goes on with the Bazaar; the repeat guard never leaves the game
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(zonenav, 'allowed', lambda graph, area: frozenset((area,)))
    walk = passage_game(monkeypatch).play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    assert ('walk', 82) not in walk.moves
    assert 'Macro: zone: Kurast Causeway (82) blocked: its way in from Upper Kurast was made 6 times' in caplog.text
    assert 'Upper Kurast (81) cleared, without [82]' in caplog.text
    assert 80 in walk.levels  # the Bazaar after it


@pytest.mark.usefixtures('zone')
def test_a_run_that_ends_at_a_temples_door_is_followed_by_the_press_into_it_not_another_run(monkeypatch):
    # 14:10:58.7-14:11:00.1 on 2026-10-21: Upper Kurast's run ended "at Forgotten Reliquary: going through takes a
    # press" 6 times in 1.4 s, the city's runs spent (RUNS_AN_AREA + its children) and it judged explored with its
    # rooms unseen. A run that ends at the chosen child's door is followed by that child's NEXT_LEVEL
    game = act_3(monkeypatch)

    def run_of(area: int) -> None:
        step = game.game.progress.step(area)
        if area == UPPER_KURAST and step is not None and step.stage.kind == ENTER and step.stage.to in (96, 97):
            game.game.at_door.add(area)  # the run went to the temple's door as it passed it, and stands there

    game.on_run = run_of
    walk = game.play()

    assert walk.stopped is None, (walk.stopped, walk.where)
    city = [index for index, area in enumerate(walk.runs) if area == UPPER_KURAST]
    assert len(city) == 3  # to the Reliquary's door, to the Temple's door, then the rest of its rooms
    assert walk.runs[city[0] + 1] == 96
    assert walk.runs[city[1] + 1] == 97
    assert UPPER_KURAST not in game.game.loop.agenda.blocked
    assert between(walk.moves, ('door', 96), ('door', UPPER_KURAST))
    assert between(walk.moves, ('door', 97), ('door', UPPER_KURAST))
