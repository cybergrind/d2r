"""TZ leveling's level run on the Frozen Tundra, 2026-10-19 21:04-21:11 (rca/2026-10-19/tz-leveling-findings.md):
the tour's stop beside the character (C1), rooms of wall alone (C2), a passed stop (C3), what strikes at the party
(C4), and the card's door on a level with no route stage (C5)."""

import math
from dataclasses import replace

from inventory_tracking.levels.model import Ground, Target, Walkable, pack_cells
from inventory_tracking.macros.agenda import COVER, ON_THE_WAY, Agenda
from inventory_tracking.macros.goals import PLACE_NEAR, Goal
from inventory_tracking.macros.hunt import Bearings
from inventory_tracking.macros.hunting import choice
from inventory_tracking.macros.hunting.base import passing_key
from inventory_tracking.macros.pursuit import FULL, Pursuit
from inventory_tracking.macros.runmode import AGENDA, Mode
from inventory_tracking.macros.travel import PRESSED
from inventory_tracking.native.layout import TILE_UNITS
from inventory_tracking.routes.model import ENTER, FIGHT
from tests.inventory_tracking.macros.test_hunt import EAST, HERE, ROOMS, foe, game, hunter, me


RECT = (1920, 0, 2560, 1418)
FLOOR = tuple(Walkable(room.x, room.y, 8, 8, pack_cells('1' * 1600)) for room in ROOMS)
BORDER = (5017.5, 5002.5)  # HERE's east edge tile, 5 units from EAST[0]'s first tile: the stand of 21:05:19


def bounds(room) -> tuple[int, int, int, int]:
    return (room.x, room.y, room.width, room.height)


def at_border(explored):
    play = game()
    hunt = hunter(play, ground=FLOOR, explored=explored)
    assert hunt.level is not None
    level = hunt.level()
    assert level is not None
    player = replace(me(play.world), x=BORDER[0], y=BORDER[1])
    return play, hunt, level, player


def place_of(found) -> tuple[float, float]:
    _, _, (x, y) = found
    return ((x + 0.5) * TILE_UNITS, (y + 0.5) * TILE_UNITS)


def test_a_tour_stop_is_past_the_arrival_distance_so_its_room_is_entered():
    # 21:05:19: the stop (10077.5, 9842.5) was 5.0 from the character in the room beside it: "at" with no move, the
    # room never entered, 15 s by 29 hostiles. Its tile is now one the arrival only counts from inside the room.
    _, hunt, level, player = at_border([bounds(room) for room in (HERE, *EAST[1:])])
    found = hunt.frontier(level, player, RECT)
    assert found is not None
    assert found[1] == EAST[0]
    assert math.dist(BORDER, place_of(found)) > PLACE_NEAR
    tile = found[2]
    assert EAST[0].x <= tile[0] < EAST[0].x + 8


def test_a_passed_stop_yields_to_the_next_stop_of_the_tour():
    # 21:05:43: the tour's first stop passed, the agenda had no target and the run ended, half the level unseen
    _, hunt, level, player = at_border([bounds(room) for room in (HERE, EAST[1], EAST[2])])
    first = hunt.frontier(level, player, RECT)
    assert first is not None
    room = first[1]

    def passed(place):
        return passing_key(place, None, level.rooms) == passing_key(place_of(first), None, level.rooms)

    other = hunt.frontier(level, player, RECT, passed)
    assert other is not None
    assert other[1] != room
    assert hunt.frontier(level, player, RECT, lambda place: True) is None


def test_the_run_looks_past_a_passed_room_at_once_and_keeps_no_empty_answer():
    play, hunt, level, player = at_border([bounds(room) for room in (HERE, EAST[1], EAST[2])])
    run = play.run()
    first = hunt.next_room(run, player, level.area, 10.0)
    assert first is not None
    goal = Goal('full clear: an unexplored room', first[0], 'reach', PLACE_NEAR, PRESSED, clearing=True)
    hunt.pass_by(goal, 'no strike and no progress', 10.0, level.rooms)
    second = hunt.next_room(run, player, level.area, 10.2)  # within REST_SECONDS: the pass looked again
    assert second is not None
    assert passing_key(second[0], None, level.rooms) != passing_key(first[0], None, level.rooms)
    hunt.explored = lambda area: {bounds(room) for room in ROOMS}
    hunt.rest = None
    assert hunt.next_room(run, player, level.area, 11.0) is None
    assert hunt.rest is None  # nothing to go to is asked again at the next look


def agenda_hunt(policy: str):
    play = game(area=117)
    hunt = hunter(play)
    hunt.agenda, hunt.agenda_policy = Agenda(), lambda area: policy
    hunt.agenda.begin('g')
    hunt.pursuit = Pursuit('pickup', 10.0, advance=False, leash=FULL, looped=True, agenda=True)
    hunt.mode = Mode(True, AGENDA, agenda=True)
    return play, hunt, play.run()


def test_tz_leveling_meets_a_white_monster_that_strikes_at_the_party_and_leaves_one_that_stands(monkeypatch):
    # 21:05:24-34: skeleton archers (txt 576) in their attack mode 25 away, the run stood 10 s. The player, ~21:15:
    # "don't waste time awaiting when mobs engage us and do it procatively". A white one standing is still left.
    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Infernal Pit')
    for policy in (COVER, ON_THE_WAY):
        play, hunt, run = agenda_hunt(policy)
        archer = replace(foe(32, 5025.0, 5000.0, txt_id=576), mode=4)
        goal = hunt.cleared(run, play.world, [archer], Ground(()), door)
        assert goal is not None
        assert (goal.do, goal.unit, goal.clearing) == (FIGHT, 32, True)
        standing = foe(33, 5025.0, 5000.0, txt_id=576)
        left = hunt.cleared(run, play.world, [standing], Ground(()), door)
        assert left is not None
        assert left.unit != 33  # the route's door, or on a cover level the next room
    monkeypatch.setattr(choice, 'ENGAGE_STRIKERS', False)
    play, hunt, run = agenda_hunt(ON_THE_WAY)
    assert hunt.cleared(run, play.world, [replace(archer, unit_id=34)], Ground(()), door) == door


def test_a_tz_run_with_no_route_stage_takes_no_other_levels_door_from_the_card():
    # 21:05:44: the Infernal Pit's red portal is a pending stage, so the card's first mark, Ancients' Way's door,
    # was the run's goal. The player's own teleport press still goes to it.
    play, hunt, run = agenda_hunt(COVER)
    card = Target(117, (), (1000.0, 1060.0), "Ancients' Way", 'exit', True)
    hunt.bearings = Bearings(card=lambda: card)
    looped = hunt.pursuit
    assert looped is not None
    assert hunt.goal(run, play.world, [], False, looped) is None
    pressed = Pursuit('teleport', run.clock(), leash=FULL, agenda=True)
    found = hunt.goal(run, play.world, [], True, pressed)
    assert found is not None
    assert found.label == "Ancients' Way"


def test_a_room_stop_stood_at_with_no_strike_is_passed_in_two_seconds_not_ten():
    # 22:00:31.9-41.9 and 22:01:00.2-10.3 (game 31, the Chaos Sanctuary): "at" a room's stop, 10 s with no strike
    # before the pass. A Herald's stand is still waited at.
    play, hunt, run = agenda_hunt(COVER)
    player = me(play.world)
    here = (player.x, player.y)
    room = Goal('full clear: an unexplored room', here, 'reach', PLACE_NEAR, PRESSED, known=False, clearing=True)
    stand = replace(room, label='full clear: the stand for the Herald coming')
    for goal, kept in ((room, False), (stand, True)):
        went = [hunt.goes_on(run, play.world, Ground(()), goal, (), now) for now in (10.0, 11.0, 12.0, 12.5)]
        assert went == [True, True, True, kept]


def test_a_tz_run_does_not_walk_or_carry_into_a_level_off_its_trip():
    # Games 30 and 31 (2026-10-19 21:51:37, 21:59:34): "Run: on into The Chaos Sanctuary" from the River of Flame,
    # a level of no trip of the zone's.
    from inventory_tracking.macros.build import NoWay
    from inventory_tracking.macros.goals import PASSAGE_NEAR
    from inventory_tracking.macros.pursuit import Ended, Facts, carried, heading, to_the_door

    passage = Target(107, (), (1000.0, 1000.0), 'Chaos Sanctum', 'exit', passage=(1000.0, 990.0), into=108)
    door = Goal('Chaos Sanctum', (5000.0, 4950.0), ENTER, PASSAGE_NEAR, PRESSED, mark=passage, route='Diablo')
    run = Pursuit('pickup', 10.0, advance=False, leash=FULL, area=107, looped=True, agenda=True)
    facts = Facts(11.0, door, False, False, True, lambda: NoWay('none'), 107)
    kept = replace(run, allowed=frozenset((107,)))
    assert heading(kept, door) is None
    assert carried(replace(kept, onward=108), 108, 12.0) is None
    ended = to_the_door(facts, door, kept)
    assert isinstance(ended, Ended)
    assert 'off the trip' in ended.reason
    onward = replace(run, allowed=frozenset((107, 108)))  # on the trip: through, as before
    noted = heading(onward, door)
    assert noted is not None
    assert noted.onward == 108
    assert carried(noted, 108, 12.0) is not None
    assert not isinstance(to_the_door(facts, door, onward), Ended)


def test_a_level_only_crossed_fights_what_strikes_at_the_party_not_its_leaders():
    from inventory_tracking.macros.agenda import TRANSIT
    from tests.inventory_tracking.macros.test_hunt import CHAMPION

    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Mephisto')
    play, hunt, run = agenda_hunt(TRANSIT)
    champion = foe(31, 5020.0, 5000.0, flags=CHAMPION)
    assert hunt.cleared(run, play.world, [champion], Ground(()), door) == door
    striker = replace(foe(32, 5020.0, 5000.0), mode=4)
    goal = hunt.cleared(run, play.world, [champion, striker], Ground(()), door)
    assert goal is not None
    assert (goal.do, goal.unit) == (FIGHT, 32)


def test_a_boss_fight_by_an_empty_mark_is_left_after_its_wait_and_the_level_explored(monkeypatch):
    # 22:49:08-53 on 2026-10-19 (Flayer Dungeon Level 3, take 20261019T194857Z-91): "Witch Doctor Endugu, by its mark
    # Khalim's Brain: nothing in reach here yet", 45 s with 8 hostiles 56 away and Endugu never in the unit table, then
    # the no-move watchdog left the game. Diablo, whom the game brings to his mark after the seals, is still waited for.
    from inventory_tracking.macros.build import NoWay
    from inventory_tracking.macros.hunting.base import MARK_WAIT
    from inventory_tracking.routes.model import fight

    play, hunt, run = agenda_hunt(ON_THE_WAY)
    player = me(play.world)
    here = (player.x, player.y)
    mark = Target(117, (), (here[0] / TILE_UNITS, here[1] / TILE_UNITS), "Khalim's Brain", 'target', True)
    stage = fight('Witch Doctor Endugu', "Khalim's Brain")
    by_mark = Goal(
        "Witch Doctor Endugu, by its mark Khalim's Brain", here, FIGHT, 20.0, PRESSED, mark=mark,
        route='Flayer Dungeon', stage=stage,
    )  # fmt: skip
    empty = NoWay(f'{by_mark.label}: nothing in reach here yet', arrived=True)
    key = (play.world.game_name, player.area, 'Witch Doctor Endugu')
    hunt.empty_mark(play.world, by_mark, empty, 100.0)
    hunt.empty_mark(play.world, by_mark, empty, 100.0 + MARK_WAIT - 0.1)
    assert key not in hunt.marks_empty  # a short wait, as for a boss that walks up
    hunt.empty_mark(play.world, by_mark, empty, 100.0 + MARK_WAIT)
    assert key in hunt.marks_empty
    assert (play.world.game_name, player.area) in hunt.wayless  # the agenda explores the level for it (COVER)
    # The route's goal is no longer the empty mark: the run goes on to what the agenda has, or ends
    monkeypatch.setattr(choice, 'goal_of', lambda *_a, **_k: by_mark)
    assert hunt.goal(run, play.world, [], False, hunt.pursuit) is None
    # Diablo's mark is waited at
    diablo = replace(by_mark, label='Diablo, by its mark Diablo', stage=fight('Diablo', 'Diablo'))
    hunt.empty_mark(play.world, diablo, empty, 200.0)
    hunt.empty_mark(play.world, diablo, empty, 260.0)
    assert (play.world.game_name, player.area, 'Diablo') not in hunt.marks_empty


def test_a_seek_of_a_boss_not_known_yet_is_left_after_the_seek_wait_and_a_wave_counts_it_afresh(monkeypatch):
    # 04:44:37-04:45:22 on 2026-10-20 (Throne of Destruction, take 20261020T014314Z-131): "seek Lister the Tormentor:
    # nothing in reach here yet" with no living hostile in the read, until the no-move watchdog left the game
    from inventory_tracking.macros.build import NoWay
    from inventory_tracking.macros.hunting.base import SEEK_WAIT
    from inventory_tracking.macros.pursuit import Hold
    from inventory_tracking.routes.model import fight

    play, hunt, _run = agenda_hunt(ON_THE_WAY)
    player = me(play.world)
    here = (player.x, player.y)
    seek = Goal(
        'seek Lister the Tormentor: toward an unexplored room', here, FIGHT, 20.0, PRESSED, known=False,
        route='Baal', stage=fight('Lister the Tormentor', 'Throne'),
    )  # fmt: skip
    empty = NoWay(f'{seek.label}: nothing in reach here yet', arrived=True)
    key = (play.world.game_name, player.area, 'Lister the Tormentor')
    hunt.empty_mark(play.world, seek, empty, 100.0)
    hunt.empty_mark(play.world, seek, empty, 100.0 + SEEK_WAIT - 1)
    hunt.empty_mark(play.world, seek, Hold(seek), 100.0 + SEEK_WAIT - 0.5)  # a wave: fought
    hunt.empty_mark(play.world, seek, empty, 100.0 + SEEK_WAIT)
    hunt.empty_mark(play.world, seek, empty, 100.0 + 2 * SEEK_WAIT - 1)
    assert key not in hunt.marks_empty  # counted from the wave's end
    hunt.empty_mark(play.world, seek, empty, 100.0 + 2 * SEEK_WAIT)
    assert key in hunt.marks_empty
    assert (play.world.game_name, player.area) in hunt.wayless


def test_the_tour_stop_gone_to_is_kept_unless_one_much_nearer_comes_up():
    # 21:53:40-56 on 2026-10-19 (the Chaos Sanctuary): to and fro between two stops 200 units apart four times, the
    # tour's first stop asked anew at every look (rca/2026-10-19/game30-run-findings.md S3)
    from inventory_tracking.macros.hunting import base

    play = game()
    hunt = hunter(play, ground=FLOOR, explored=[bounds(HERE), bounds(EAST[1])])
    assert hunt.level is not None
    level = hunt.level()
    assert level is not None

    def room(player, keep=None):
        found = hunt.frontier(level, player, RECT, keep=keep)
        assert found is not None
        return found[1]

    middle = replace(me(play.world), x=5070.0)  # in EAST[1]: EAST[0] 3 tiles off by the way, EAST[2] 6
    assert room(middle) == EAST[0]
    assert room(middle, bounds(EAST[2])) == EAST[2]  # kept: the other is not much nearer
    beside = replace(middle, x=5060.0)  # by EAST[0]: 1.4 tiles, against EAST[2]'s 8
    assert room(beside, bounds(EAST[2])) == EAST[0]  # much nearer: taken
    # next_room keeps its stop across looks
    run = play.run()
    hunt.stop_kept = (level.area, bounds(EAST[2]))
    room = hunt.next_room(run, middle, level.area, 50.0)
    assert room is not None
    assert EAST[2].x * TILE_UNITS <= room[0][0] < (EAST[2].x + 8) * TILE_UNITS
    assert base.KEEP_STOP  # the dated switch is on


def test_the_routes_seal_beside_the_character_is_gone_to_before_the_tours_far_room(monkeypatch):
    # Game 30 (the Chaos Sanctuary, 2026-10-19): after Vizier seal 1 the run went to a room 184 units off before seal 2,
    # 40 units off (rca/2026-10-19/game30-run-findings.md S3). A route's portal (a `use` leading elsewhere) is not taken
    # so: the level is explored first.
    from inventory_tracking.macros.goals import USE_NEAR
    from inventory_tracking.routes.model import USE, use

    play, hunt, run = agenda_hunt(COVER)
    player = me(play.world)
    far = ((player.x, player.y + 184.0), 'an unexplored room', None)
    monkeypatch.setattr(hunt, 'next_room', lambda *_a, **_k: far)
    seal = Goal(
        'Vizier seal 2', (player.x + 40.0, player.y), USE, USE_NEAR, PRESSED, route='Diablo', stage=use('Vizier seal 2')
    )
    goal = hunt.cleared(run, play.world, [], Ground(()), seal)
    assert goal is not None
    assert goal.label == 'Vizier seal 2'
    portal = replace(seal, label='Red portal', stage=use('Red portal', 103))
    goal = hunt.cleared(run, play.world, [], Ground(()), portal)
    assert goal is not None
    assert goal.place == far[0]


def test_a_level_whose_zone_moved_on_ends_its_run_with_a_strike_at_hand():
    # 23:30 on 2026-10-19: the zone went to Dry Hills; Spider Forest's run explored its rooms 1.5 min more
    from inventory_tracking.macros.agenda import ZONE_LEFT

    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Infernal Pit')
    play, hunt, run = agenda_hunt(ZONE_LEFT)
    archer = replace(foe(32, 5025.0, 5000.0, txt_id=576), mode=4)
    assert hunt.cleared(run, play.world, [archer], Ground(()), door) is None


def test_a_level_skipped_as_not_worth_playing_on_ends_its_run_with_a_strike_at_hand():
    # zonenav.py STALLED_SKIP (rca/2026-10-23/exp-hour-levels-findings.md): the SKIPPED policy ends the run as ZONE_LEFT
    from inventory_tracking.macros.agenda import SKIPPED

    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Infernal Pit')
    play, hunt, run = agenda_hunt(SKIPPED)
    archer = replace(foe(32, 5025.0, 5000.0, txt_id=576), mode=4)
    assert hunt.cleared(run, play.world, [archer], Ground(()), door) is None


def test_a_tz_runs_way_out_not_on_the_card_yet_takes_no_other_levels_door():
    # 01:01:26 on 2026-10-20, Lost City: "at Ancient Tunnels (Valley of Snakes is not marked yet): going through takes
    # a press" again and again, then the game left. An unexplored room is gone to instead, or nothing
    from inventory_tracking.macros.route import PERFORMED
    from inventory_tracking.routes.catalog import ROUTES
    from inventory_tracking.routes.progress import Progress

    lost_city = 44
    play = game(area=lost_city)
    hunt = hunter(play)
    hunt.agenda, hunt.agenda_policy = Agenda(), lambda area: COVER
    hunt.agenda.begin('g')
    tunnels = Target(lost_city, (), (1000.0, 1060.0), 'Ancient Tunnels', 'exit', True)
    hunt.bearings = Bearings(Progress(ROUTES, PERFORMED, wanted=lambda area: area in (44, 45)), lambda: tunnels)
    looped = Pursuit('pickup', 10.0, advance=False, leash=FULL, looped=True, agenda=True)
    hunt.pursuit = looped
    run = play.run()
    found = hunt.goal(run, play.world, [], False, looped)
    assert found is None or found.label.startswith('seek Valley of Snakes')
    pressed = Pursuit('teleport', run.clock(), leash=FULL, agenda=True)  # the player's own press keeps the card's
    by_hand = hunt.goal(run, play.world, [], True, pressed)
    assert by_hand is not None
    assert by_hand.label.startswith('Ancient Tunnels')


def test_a_route_goal_with_no_way_after_its_level_was_explored_ends_the_run(monkeypatch):
    # 01:04:16-01:05:01 on 2026-10-20, Lost City: "no way toward Valley of Snakes" after the rooms were explored, 45 s
    # idle and the watchdog left the game. Now the run ends NO_WAY_ENDS after
    from inventory_tracking.macros.build import NoWay
    from inventory_tracking.macros.hunting import judging
    from inventory_tracking.macros.hunting.base import NO_WAY_ENDS
    from inventory_tracking.macros.pursuit import Ended

    play, hunt, run = agenda_hunt(COVER)
    player = me(play.world)
    door = Goal('Valley of Snakes', (player.x + 300.0, player.y), ENTER, PLACE_NEAR, PRESSED, route='Claw Viper Temple')
    monkeypatch.setattr(choice, 'goal_of', lambda *_a, **_k: door)
    monkeypatch.setattr(hunt, 'agenda_cleared', lambda run, world, foes, ground, found: found)
    stuck = NoWay('no way toward Valley of Snakes: no way of hops leads over the rooms to the goal')
    monkeypatch.setattr(judging, 'decide', lambda *_a, **_k: stuck)
    hunt.wayless.add((play.world.game_name, player.area))
    play.clock.now = 100.0
    assert hunt.judge(run, play.world, [], Ground(()), in_reach=False).act == stuck
    play.clock.now = 100.0 + NO_WAY_ENDS - 0.5
    assert hunt.judge(run, play.world, [], Ground(()), in_reach=False).act == stuck
    play.clock.now = 100.0 + NO_WAY_ENDS
    last = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
    assert isinstance(last.act, Ended)


def test_the_passage_into_valley_of_snakes_has_a_way_of_hops_over_lost_city():
    # 01:01-01:17 on 2026-10-20, five games: "no way toward Valley of Snakes: no way of hops leads over the rooms to the
    # goal" after all of Lost City; the border mark's far place lay past the cliff of room 379, a potential of one tile
    # (rca/2026-10-20/valley-of-snakes-findings.md). From the open edge tile the way reaches the character.
    from inventory_tracking.game.view import Viewport
    from inventory_tracking.levels.exits import passage_of
    from inventory_tracking.levels.model import Poi
    from inventory_tracking.macros.teleport import Way, footing
    from tests.inventory_tracking.levels.test_exits import CLIFF_MARK, VALLEY_OF_SNAKES, lost_city

    rooms, grids = lost_city()
    poi = Poi('Valley of Snakes', rooms[0], 'stairs', area=VALLEY_OF_SNAKES)
    here = (800.5, 1010.5)  # tiles: the canyon's foot, below the Ancient Tunnels' ruin
    assert footing(Ground(grids), here)

    def way_from_here(passage):
        target = Target(44, rooms, passage, 'Valley of Snakes', 'stairs', False, grids, passage=passage, into=45)
        return Way(target, Viewport(RECT[2] / RECT[3]), True).from_here(here)

    cliff = passage_of(44, rooms, poi, CLIFF_MARK)
    assert cliff is not None
    assert way_from_here(cliff) == math.inf  # the run's dead end, kept as the evidence
    passage = passage_of(44, rooms, poi, CLIFF_MARK, grids)
    assert passage is not None
    assert way_from_here(passage) < 20.0


def agenda_chest_run(place_east: float = 5.0):
    """The Sewers Level 1 super chest of 01:52-01:54 on 2026-10-20: one chest, seen under two names before the
    third, the one opened (rca/2026-10-20/super-chest-settle-findings.md)."""
    from inventory_tracking.game.records import Thing

    play, hunt, run = agenda_hunt(COVER)
    player = me(play.world)
    place = (player.x + place_east, player.y)
    return play, hunt, run, place, Thing(465277632, 397, 0, *place), Thing(2426831358, 397, 0, *place)


def test_a_super_chest_named_anew_by_the_client_is_one_goal_and_once_open_no_goal():
    # 01:54:14-01:55:00 on 2026-10-20: the chest opened (unit 2426831358, mode 2), and the agenda kept the closed
    # goals of its earlier names (465277632, 3554253911) at the same place: "At Super chest" for 45 s
    from inventory_tracking.routes.model import USE

    play, hunt, run, place, before, now = agenda_chest_run()
    run.things = lambda: (before,)
    goal = hunt.cleared(run, play.world, [], Ground(()), None)
    assert goal is not None
    assert (goal.do, goal.unit) == (USE, before.unit_id)
    run.things = lambda: (now,)  # its room loaded again: the same chest, a new unit
    goal = hunt.cleared(run, play.world, [], Ground(()), None)
    assert goal is not None
    assert (goal.do, goal.unit) == (USE, now.unit_id)
    run.things = lambda: (replace(now, mode=2, selectable=False),)  # opened
    after = hunt.cleared(run, play.world, [], Ground(()), None)
    assert after is None or after.place != place


def test_a_super_chest_found_open_at_its_use_waits_for_nothing_and_its_goal_is_left():
    # The same incident: every re-use of the opened chest renewed the 0.1 s wait (teleport.py CHEST_BRINGS), so the
    # look after stood ("what the object used brings comes first") and the one after used it again. A goal whose
    # unit is out of sight (a name the client has dropped) is left after SUPER_TRIES uses all the same.
    from inventory_tracking.macros.hunting.base import SUPER_TRIES

    play, hunt, run, place, before, now = agenda_chest_run()
    run.things = lambda: (before,)
    goal = hunt.cleared(run, play.world, [], Ground(()), None)
    assert goal is not None
    assert goal.unit == before.unit_id
    run.things = lambda: (replace(now, mode=2, selectable=False),)  # opened under its new name, unseen closed
    settled = hunt.settled_at
    for _ in range(SUPER_TRIES):
        hunt.operate(run, play.world, goal, None)  # "At Super chest": used already
        assert hunt.settled_at == settled
    after = hunt.cleared(run, play.world, [], Ground(()), None)
    assert after is None or after.place != place


# -- the Maggot Lair's super chests (the player, ~09:35 on 2026-10-20: "we need to open superchests when we
# encountering them"; rca/2026-10-20/superchest-findings.md): TombChest1/2 at the treasure rooms' PlaceUniqueChest
# spots, passed closed because only class 397 counted --

LAIR = 505  # Act 2 - Lair Treasure W: its one layout places the unique chests at (35, 21) and (26, 34) units
TOMB_CHEST = 88  # TombChest2, the class the game rolled at those spots in the takes


def lair_run(*things):
    """TZ leveling with a Lair treasure room south of the character's; the chest spots 44 and 54 units away."""
    from inventory_tracking.levels.model import Level, Room

    play, hunt, run = agenda_hunt(COVER)
    room = Room(LAIR, 996, 1004, 10, 10, 0, (996, 1004, 10, 10))
    rooms = (*ROOMS, room)
    hunt.level = lambda: Level(me(play.world).area, rooms, ())
    run.things = lambda: things
    return play, hunt, run


def lair_chest(unit: int = 1803365275, mode: int = 0, spot: tuple[float, float] = (5015.0, 5041.0)):
    from inventory_tracking.game.records import Thing

    return Thing(unit, TOMB_CHEST, mode, *spot)


def test_a_chest_at_a_unique_chest_spot_is_a_super_chest_the_agenda_opens_by_its_class(monkeypatch):
    # 09:33:24 on 2026-10-20: TombChest2 3814233991 at the Lair Prev W spot 9 units from the character, left closed
    from inventory_tracking.levels.model import UNIQUE_CHEST
    from inventory_tracking.macros import superchests
    from inventory_tracking.macros.teleport import marked_thing
    from inventory_tracking.routes.model import USE

    chest = lair_chest()
    play, hunt, run = lair_run(chest)
    goal = hunt.cleared(run, play.world, [], Ground(()), None)
    assert goal is not None
    assert (goal.do, goal.unit, goal.place) == (USE, chest.unit_id, (chest.x, chest.y))
    assert goal.mark is not None
    assert goal.mark.use == UNIQUE_CHEST
    assert marked_thing(run, goal.mark) == chest  # the act finds the rolled class at the mark
    monkeypatch.setattr(superchests, 'ENABLED', False)  # as before: the glowing chest alone
    play, hunt, run = lair_run(chest)
    before = hunt.cleared(run, play.world, [], Ground(()), None)
    assert before is None or before.unit != chest.unit_id


def test_a_chest_off_the_spots_or_opened_is_no_super_chest():
    off = lair_chest(70, spot=(5010.0, 5041.0))  # a plain chest 5 units beside the spot
    opened = lair_chest(71, mode=2)
    play, hunt, run = lair_run(off, opened)
    goal = hunt.cleared(run, play.world, [], Ground(()), None)
    assert goal is None or goal.unit not in (70, 71)


def test_a_valuable_on_the_ground_and_a_leader_in_sight_come_before_the_super_chest():
    from inventory_tracking.macros.goals import PICK_UP
    from inventory_tracking.routes.model import FIGHT
    from tests.inventory_tracking.macros.test_hunt import CHAMPION

    chest = lair_chest()
    play, hunt, run = lair_run(chest)
    ko = Goal('Ko Rune', (5003.0, 5000.0), PICK_UP, PLACE_NEAR, PRESSED, unit=9)
    assert hunt.cleared(run, play.world, [], Ground(()), ko) == ko
    champion = foe(5, 5010.0, 5000.0, flags=CHAMPION)
    goal = hunt.cleared(run, play.world, [champion], Ground(()), None)
    assert goal is not None
    assert (goal.do, goal.unit) == (FIGHT, 5)


# The Throne of Destruction's waves and portal (macros/hunting/throne.py; the player, 2026-10-20 ~09:33: "tz leveling
# should do baal and trone fight"). Places of the takes of 2026-10-11 to 2026-10-20: Baal on his throne (543) at
# (15090.5, 5011.5), the Throne mark (the stand) at (15080, 5015), the waves round (15090, 5025)
SEAT, STAND = (15090.5, 5011.5), (15080.0, 5015.0)


def wave_look(waves, found, here, hostiles=(), now=0.0, seat=SEAT, stage=None):
    from inventory_tracking.macros.hunting import throne
    from inventory_tracking.routes.model import fight

    return throne.wave_goal(
        waves, area=throne.THRONE, stage=stage or fight('Lister the Tormentor'), route='Baal', found=found,
        here=here, hostiles=hostiles, seat=seat, stand=STAND, reach=20.0, spend=PRESSED, now=now,
    )  # fmt: skip


def test_the_throne_clears_its_hall_then_waits_for_the_waves_at_the_stand_and_fights_each_wave():
    # The waves came only with the hall clear and the character by the throne (takes of 2026-10-11 00:18, 10-14, 10-17
    # 23:49); today's runs sought Lister over the whole level, 135-194 units off, and no wave came (01:43, 01:55 UTC)
    from inventory_tracking.macros.goals import REACH
    from inventory_tracking.macros.hunting import throne
    from inventory_tracking.routes.model import fight

    waves = throne.Waves()
    waves.begin('g')
    seek = Goal('seek Lister the Tormentor: toward an unexplored room', (15150.0, 5130.0), FIGHT, 20.0, PRESSED,
                known=False, route='Baal', stage=fight('Lister the Tormentor'))  # fmt: skip
    far = (15148.0, 5134.0)
    hall = foe(41, 15094.0, 5060.0, txt_id=478)  # a Hell Witch 49 from the seat, in the hall (torches to y 5064)
    outside = foe(42, 15176.0, 5066.0, txt_id=697)  # behind the east wall, 98 from the seat: not the hall's
    first = wave_look(waves, seek, far, [hall, outside])
    assert isinstance(first, Goal)
    assert (first.do, first.unit, first.clearing) == (FIGHT, 41, True)  # the hall first
    to_stand = wave_look(waves, seek, far, [outside], now=1.0)
    assert isinstance(to_stand, Goal)
    assert (to_stand.do, to_stand.place, to_stand.stage) == (REACH, STAND, seek.stage)
    assert not waves.due(1.0)  # away from the stand nothing is waited for
    at = (15081.0, 5016.0)
    waiting = wave_look(waves, seek, at, [], now=2.0)
    assert waiting == to_stand
    assert waves.due(2.0)
    assert waves.due(2.0 + throne.DUE_GRACE)
    assert not waves.due(2.1 + throne.DUE_GRACE)
    # A wave: its boss in sight is the fight (goal_of names him), and the wait counts afresh from its end
    colenzo = Goal('Lister the Tormentor', (15090.0, 5026.0), FIGHT, 20.0, PRESSED, unit=61, route='Baal',
                   stage=seek.stage)  # fmt: skip
    assert wave_look(waves, colenzo, at, [], now=2.0 + throne.WAVE_WAIT - 1) == colenzo
    minion = foe(43, 15092.0, 5030.0, txt_id=23)  # its boss dead, a minion left: fought before the next wave
    left = wave_look(waves, seek, at, [minion], now=2.0 + throne.WAVE_WAIT)
    assert isinstance(left, Goal)
    assert left.unit == 43
    again = 3.0 + throne.WAVE_WAIT
    assert wave_look(waves, seek, at, [], now=again) == to_stand
    assert wave_look(waves, seek, at, [], now=again + throne.WAVE_WAIT - 0.1) == to_stand  # still waited
    assert throne.THRONE_WAVES  # the dated switch is on


def test_a_throne_where_no_wave_comes_gives_its_stage_up_and_the_level_is_explored(monkeypatch):
    # The loop never hangs: WAVE_WAIT at the stand with nothing coming leaves the stage as an empty mark does; a seek's
    # SEEK_WAIT (20 s) no longer ends the Throne's wait
    from inventory_tracking.macros.hunt import Bearings
    from inventory_tracking.macros.hunting import throne
    from inventory_tracking.macros.hunting.base import SEEK_WAIT
    from inventory_tracking.routes.model import fight

    play = game(area=throne.THRONE)
    play.world = replace(play.world, player=replace(me(play.world), x=STAND[0] + 1, y=STAND[1]))
    hunt = hunter(play)
    hunt.agenda, hunt.agenda_policy = Agenda(), lambda area: ON_THE_WAY
    hunt.agenda.begin('g')
    hunt.pursuit = Pursuit('pickup', 10.0, advance=False, leash=FULL, looped=True, agenda=True)
    hunt.mode = Mode(True, AGENDA, agenda=True)
    hunt.bearings = Bearings(marks=lambda label: ((3016.0, 1003.0),) if label == 'Throne' else ())
    stage = fight('Lister the Tormentor')
    seek = Goal('seek Lister the Tormentor: toward an unexplored room', (15150.0, 5130.0), FIGHT, 20.0, PRESSED,
                known=False, route='Baal', stage=stage)  # fmt: skip
    monkeypatch.setattr(choice.route, 'staged', lambda progress, area: ('Baal', stage))
    monkeypatch.setattr(choice, 'goal_of', lambda *_a, **_k: seek)
    clock = [100.0]
    run = play.run()
    run.clock = lambda: clock[0]
    found = hunt.goal(run, play.world, [], False, hunt.pursuit)
    assert found is not None
    assert found.label.endswith(throne.WAVES_STAND)
    clock[0] += SEEK_WAIT + 1
    assert hunt.goal(run, play.world, [], False, hunt.pursuit) == found  # waited past a seek's give-up
    key = (play.world.game_name, throne.THRONE, 'Lister the Tormentor')
    assert key not in hunt.marks_empty
    clock[0] = 100.0 + throne.WAVE_WAIT
    assert hunt.goal(run, play.world, [], False, hunt.pursuit) is None
    assert key in hunt.marks_empty
    assert (play.world.game_name, throne.THRONE) in hunt.wayless  # the agenda explores the level (COVER), then ends
    assert not hunt.waves.due(clock[0])
    assert hunt.goal(run, play.world, [], False, hunt.pursuit) is None  # given up for the game
    # A run that is not the agenda's (a KP_1 press) keeps the route's goal as before
    hunt.marks_empty.clear()
    hunt.pursuit = Pursuit('pickup', 10.0, advance=False, leash=FULL)
    assert hunt.goal(run, play.world, [], False, hunt.pursuit) == seek


def test_after_the_waves_the_stand_is_kept_until_baal_leaves_then_the_portal_and_a_portal_that_never_opens_ends():
    # 00:18 on 2026-10-11: the fifth wave died ~119 s, Baal (543) gone into the portal at 127.5 s, the player's click
    # on the portal at 133.3 s, the Worldstone Chamber at 133.6 s
    from inventory_tracking.macros.goals import USE
    from inventory_tracking.macros.hunting import throne
    from inventory_tracking.routes.model import use

    waves = throne.Waves()
    waves.begin('g')
    stage = use('Worldstone Chamber', throne.CHAMBER)
    portal = Goal('Worldstone Chamber', (15090.0, 5005.0), USE, 25.0, PRESSED, route='Baal', stage=stage)
    at = (15081.0, 5016.0)
    waiting = wave_look(waves, portal, at, now=10.0, stage=stage)
    assert isinstance(waiting, Goal)
    assert waiting.label.endswith(throne.PORTAL_WAIT)
    assert waiting.place == STAND
    assert waves.due(10.0)
    # The player, 2026-10-21 ~17:41: "1. wait for baal disappears 2. go near portal, wait for a few seconds 3. go
    # through portal"
    foot = throne.foot_of(portal.place)
    assert foot == (15090.5, 5009.0)  # where the player's entry of 17:38:17.8 stood
    going = wave_look(waves, portal, at, now=12.0, seat=None, stage=stage)  # he left: to the portal's foot
    assert isinstance(going, Goal)
    assert (going.label, going.place) == (f'Worldstone Chamber: {throne.PORTAL_NEAR}', foot)
    assert waves.due(12.0)
    there = (15090.6, 5009.2)
    opening = wave_look(waves, portal, there, now=13.0, seat=None, stage=stage)
    assert isinstance(opening, Goal)
    assert (opening.label, opening.place) == (f'Worldstone Chamber: {throne.PORTAL_OPENING}', foot)
    assert wave_look(waves, portal, there, now=13.0 + throne.FOOT_WAIT - 0.1, seat=None, stage=stage) != portal
    assert wave_look(waves, portal, there, now=13.0 + throne.FOOT_WAIT, seat=None, stage=stage) == portal
    stuck = throne.Waves()
    stuck.begin('g')
    assert wave_look(stuck, portal, at, now=0.0, stage=stage) != portal
    assert wave_look(stuck, portal, at, now=throne.BAAL_LEAVES, stage=stage) != portal  # never under him
    assert wave_look(stuck, portal, at, now=throne.BAAL_LEAVES + throne.PORTAL_SECONDS, stage=stage) is None
    # A new game forgets
    stuck.begin('h')
    assert wave_look(stuck, portal, at, now=500.0, stage=stage) != portal
    # Off the Throne nothing changes
    assert (
        throne.wave_goal(
            waves, area=throne.CHAMBER, stage=stage, route='Baal', found=portal, here=at, hostiles=(), seat=SEAT,
            stand=STAND, reach=20.0, spend=PRESSED, now=0.0,
        )
        == portal
    )  # fmt: skip


def test_baal_walking_into_the_portal_is_still_baal_and_the_portal_waits_until_he_is_gone_and_it_opens():
    # The four takes that saw him go (2026-10-11 00:12 and 00:18, 10-14 16:37, 10-17 20:49): the same unit turned from
    # 543 into 559 (`baalcrabstairs`) 10.1-11.3 s after the fifth wave's last monster died, walked from y 5012 to 5008
    # and was gone from the read 0.5-1.6 s later. 00:18: 543 to 559 at 127.57 s, gone at 128.33 s
    from inventory_tracking.game.records import Monster
    from inventory_tracking.macros.goals import USE
    from inventory_tracking.macros.hunting import throne
    from inventory_tracking.macros.hunting.base import hostiles
    from inventory_tracking.routes.model import use

    seated = Monster(1179846619, 543, 1, 15090.0, 5012.0)
    walking = replace(seated, txt_id=559, mode=2, y=5009.0)
    assert throne.seat_of([seated]) == (15090.0, 5012.0)
    assert throne.seat_of([walking]) == (15090.0, 5009.0)
    assert throne.seat_of([]) is None
    play = game(area=throne.THRONE)
    assert not hostiles(replace(play.world, monsters=(seated, walking)))  # neither is ever struck

    waves = throne.Waves()
    waves.begin('g')
    stage = use('Worldstone Chamber', throne.CHAMBER)
    portal = Goal('Worldstone Chamber', (15090.0, 5005.0), USE, 25.0, PRESSED, route='Baal', stage=stage)
    at = (15081.0, 5016.0)
    assert wave_look(waves, portal, at, now=118.5, stage=stage) != portal  # the hall clear, 543 on his throne
    on_his_way = wave_look(waves, portal, at, now=127.6, seat=throne.seat_of([walking]), stage=stage)
    assert isinstance(on_his_way, Goal)
    assert on_his_way.label.endswith(throne.PORTAL_WAIT)  # 559: not clicked under him
    assert wave_look(waves, portal, at, now=128.3, seat=None, stage=stage) != portal  # gone: the portal opens
    # A read that has him again (a look from farther that missed him) counts his going afresh
    assert wave_look(waves, portal, at, now=128.4, seat=SEAT, stage=stage) != portal
    assert wave_look(waves, portal, at, now=128.5, seat=None, stage=stage) != portal
    foot = throne.foot_of(portal.place)
    assert wave_look(waves, portal, foot, now=128.5 + throne.FOOT_WAIT - 0.01, seat=None, stage=stage) != portal
    assert wave_look(waves, portal, foot, now=128.5 + throne.FOOT_WAIT, seat=None, stage=stage) != portal
    assert wave_look(waves, portal, foot, now=128.6 + throne.FOOT_WAIT, seat=None, stage=stage) != portal
    assert wave_look(waves, portal, foot, now=131.6 + throne.FOOT_WAIT, seat=None, stage=stage) == portal


def test_with_baal_on_his_throne_the_portal_stage_clears_the_hall_and_his_wait_counts_from_its_clear():
    # He left 10-11 s after the fifth wave's last monster died, never with one alive (the four takes); a minion of
    # Lister's left in the hall is fought, and the BAAL_LEAVES wait counts from the hall's clear
    from inventory_tracking.macros.goals import USE
    from inventory_tracking.macros.hunting import throne
    from inventory_tracking.routes.model import use

    waves = throne.Waves()
    waves.begin('g')
    stage = use('Worldstone Chamber', throne.CHAMBER)
    portal = Goal('Worldstone Chamber', (15090.0, 5005.0), USE, 25.0, PRESSED, route='Baal', stage=stage)
    at = (15081.0, 5016.0)
    minion = foe(44, 15095.0, 5040.0, txt_id=571)  # 29 from the seat
    far = foe(45, 15200.0, 5200.0, txt_id=571)  # off in the level: not the hall's
    fought = wave_look(waves, portal, at, [minion, far], now=0.0, stage=stage)
    assert isinstance(fought, Goal)
    assert (fought.do, fought.unit, fought.clearing) == (FIGHT, 44, True)
    assert fought.label == 'Worldstone Chamber: the throne hall first (1 left)'
    assert not waves.due(0.0)  # a fight moves: no wait to cover
    assert wave_look(waves, portal, at, [far], now=20.0, stage=stage) != portal  # clear from 20 s
    assert wave_look(waves, portal, at, [far], now=20.0 + throne.BAAL_LEAVES - 0.1, stage=stage) != portal
    assert wave_look(waves, portal, at, [far], now=20.0 + throne.BAAL_LEAVES, stage=stage) != portal  # never under him
    # A passed one (the clearing judge's: no progress) does not hold it
    passed = throne.wave_goal(
        throne.Waves(), area=throne.THRONE, stage=stage, route='Baal', found=portal, here=at, hostiles=[minion],
        seat=SEAT, stand=STAND, reach=20.0, spend=PRESSED, now=0.0, passed=lambda m: m.unit_id == 44,
    )  # fmt: skip
    assert isinstance(passed, Goal)
    assert passed.label.endswith(throne.PORTAL_WAIT)
    # The stage's bound stands whatever the hall holds: the run ends
    assert wave_look(waves, portal, at, [minion], now=throne.BAAL_LEAVES + throne.PORTAL_SECONDS, stage=stage) is None


def test_the_portal_stage_clicks_the_thrones_portal_and_in_the_chamber_baal_is_the_goal():
    # The portal hop (levels/model.py CLICKED, teleport.py USES[THRONE_PORTAL]) and Baal (544) in the Worldstone
    # Chamber by the boss lairs' mark (135, 160) of wstone01.ds1
    from inventory_tracking.game.records import Monster, Thing
    from inventory_tracking.levels.model import THRONE_PORTAL
    from inventory_tracking.macros.goals import USE, route_goal
    from inventory_tracking.macros.teleport import USES, marked_thing
    from inventory_tracking.routes.catalog import ROUTES
    from inventory_tracking.routes.model import use

    baal = next(found for found in ROUTES if found.name == 'Baal')
    throne = next(script for script in baal.scripts if script.area == 131)
    chamber = next(script for script in baal.scripts if script.area == 132)
    portal_stage = next(stage for stage in throne.stages if stage.kind == USE)
    assert portal_stage == use('Worldstone Chamber', 132)
    card = Target(131, (), (3018.0, 1001.0), 'Worldstone Chamber', 'target', use=THRONE_PORTAL)
    goal = route_goal((15081.0, 5016.0), spend=PRESSED, reach=20.0, stage=portal_stage, route='Baal', card=card)
    assert goal is not None
    assert (goal.do, goal.place, goal.mark) == (USE, (15090.0, 5005.0), card)
    assert USES[THRONE_PORTAL].leaves  # it took when the level changed

    class Seen:
        things = staticmethod(lambda: (Thing(9, THRONE_PORTAL, 0, 15090, 5005),))

    found = marked_thing(Seen(), card)  # pyrefly: ignore[bad-argument-type] a stand-in run with the reads only
    assert found is not None
    assert found.unit_id == 9
    fight_baal = next(stage for stage in chamber.stages if stage.kind == FIGHT)
    mark = Target(132, (), (3027.0, 1176.0), 'Baal', 'target')
    baal_544 = Monster(77, 544, 1, 15137.0, 5880.0, 0xFFFFFFFF, 0)
    goal = route_goal(
        (15173.5, 5888.5), spend=PRESSED, reach=20.0, stage=fight_baal, route='Baal', card=mark, foes=[baal_544]
    )
    assert goal is not None
    assert (goal.do, goal.unit) == (FIGHT, 77)


# -- the level's super chests before it is left (the player, ~09:52 on 2026-10-20: "nope, in maggot layer 3 superchest
# wasn't opened", "in coldworm's room there was a glowing chest - we always should try to open such chests whenever we
# encountered them"; the take 20261020T065019Z-64) --

COLDWORM = 509  # Act 2 - Lair Tight Spot S: the Staff of Kings' chest at (10, 30) units from its origin


def boss_run(monkeypatch, rooms, player):
    from inventory_tracking.levels.model import Level
    from inventory_tracking.macros import superchests
    from inventory_tracking.routes.model import FIGHT

    monkeypatch.setattr(superchests, 'BOOK', superchests.Book())
    play, hunt, run = agenda_hunt(ON_THE_WAY)
    hunt.level = lambda: Level(me(play.world).area, rooms, ())
    run.things = lambda: ()
    world = replace(play.world, player=replace(me(play.world), x=player[0], y=player[1]))
    boss = Goal('Coldworm the Burrower', (player[0], player[1] - 200.0), FIGHT, 10.0, PRESSED, route='Maggot Lair')
    return world, hunt, run, boss


def test_a_treasure_rooms_spot_far_off_the_way_is_gone_to_before_the_boss_and_dropped_once_seen_empty(monkeypatch):
    # 09:50:19-46: the Lair Treasure W spots (17676, 8234) and (17685, 8221) were 97 units east of the way north to
    # Coldworm, never read, never a goal
    from inventory_tracking.levels.model import Room
    from inventory_tracking.macros import superchests
    from inventory_tracking.macros.goals import REACH

    treasure = Room(LAIR, 996, 1030, 10, 10, 0, (996, 1030, 10, 10))  # spots (5015, 5171) and (5006, 5184)
    world, hunt, run, boss = boss_run(monkeypatch, (*ROOMS, treasure), (5000.0, 5000.0))
    goal = hunt.cleared(run, world, [], Ground(()), boss)
    assert goal is not None
    assert (goal.do, goal.place) == (REACH, (5015.0, 5171.0))
    at = replace(world, player=replace(me(world), x=5010.0, y=5178.0))  # both spots in sight: no chest read there
    assert hunt.cleared(run, at, [], Ground(()), boss) == boss
    monkeypatch.setattr(superchests, 'LEVEL_SPOTS', False)  # as before: the boss's goal, the spot left
    world, hunt, run, boss = boss_run(monkeypatch, (*ROOMS, treasure), (5000.0, 5000.0))
    assert hunt.cleared(run, world, [], Ground(()), boss) == boss


def test_the_glowing_staff_chest_in_coldworms_room_is_read_and_opened_after_coldworm(monkeypatch):
    # 09:50:35-46: the character stood at (17532.5, 8023.5), 23 units from the Staff of Kings' chest on Coldworm's
    # mark (17510, 8030); class 356 was no class the read took (game/decode.py USED), so nothing saw it
    from inventory_tracking.game.decode import USED, usable
    from inventory_tracking.game.records import Thing
    from inventory_tracking.levels.model import STAFF_CHEST, UNIQUE_CHEST, Room
    from inventory_tracking.macros.teleport import marked_thing
    from inventory_tracking.routes.model import FIGHT, USE
    from tests.inventory_tracking.macros.test_hunt import CHAMPION

    room = Room(COLDWORM, 3500, 1600, 10, 10, 0, (3500, 1600, 10, 10))
    chest = Thing(2207425023, STAFF_CHEST, 0, 17510.0, 8030.0)
    assert STAFF_CHEST in USED
    assert usable(chest)
    world, hunt, run, boss = boss_run(monkeypatch, (*ROOMS, room), (17532.5, 8023.5))
    run.things = lambda: (chest,)
    coldworm = foe(9, 17512.1, 8030.4, flags=CHAMPION)
    goal = hunt.cleared(run, world, [coldworm], Ground(()), boss)
    assert goal is not None
    assert (goal.do, goal.unit) == (FIGHT, 9)  # the boss first, the chest after
    goal = hunt.cleared(run, world, [], Ground(()), boss)
    assert goal is not None
    assert (goal.do, goal.unit) == (USE, chest.unit_id)
    assert goal.mark is not None
    assert goal.mark.use == UNIQUE_CHEST
    assert marked_thing(run, goal.mark) == chest
    run.things = lambda: (replace(chest, mode=2),)  # opened: the route's own goal again
    assert hunt.cleared(run, world, [], Ground(()), boss) == boss


def test_tz_plus_runs_fight_a_reasonable_group_of_white_monsters_and_leave_a_lone_one():
    # The player, 2026-10-20 ~18:50: "we just kill reasonable groups ... we don't want to kill alone mobs in the
    # corners"
    from inventory_tracking.macros.agenda import GROUP_MIN, PLUS

    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Andariel')
    play, hunt, run = agenda_hunt(PLUS)
    play.world = replace(play.world, player=replace(me(play.world), area=35))  # Catacombs 2: 88, under BIG_LEVEL
    whites = [foe(40 + index, 5012.0 + 6.0 * index, 5010.0) for index in range(GROUP_MIN)]
    goal = hunt.cleared(run, play.world, whites, Ground(()), door)
    assert goal is not None
    assert (goal.do, goal.unit, goal.clearing) == (FIGHT, 40, True)
    lone = foe(50, 5045.0, 4990.0)  # on the level (the east room), alone
    left = hunt.cleared(run, play.world, [lone], Ground(()), door)
    assert left is not None
    assert left.unit != 50  # the next room, then the route's door


def test_tz_plus_on_a_big_level_leaves_a_group_a_small_level_takes_and_fights_a_big_one():
    # The player, ~18:58: "fore levels with 300+ mobs - we just clear big groups and elites/champions"
    from inventory_tracking.macros.agenda import BIG_GROUP, PLUS

    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Infernal Pit')
    play, hunt, run = agenda_hunt(PLUS)  # the Frozen Tundra: 374
    small = [foe(40 + index, 5012.0 + 3.0 * index, 5010.0) for index in range(BIG_GROUP - 1)]
    left = hunt.cleared(run, play.world, small, Ground(()), door)
    assert left is not None
    assert left.unit not in {m.unit_id for m in small}
    big = [*small, foe(60, 5012.0, 5016.0)]
    goal = hunt.cleared(run, play.world, big, Ground(()), door)
    assert goal is not None
    assert (goal.do, goal.unit) == (FIGHT, 40)
    champion = foe(61, 5045.0, 4990.0, flags=0x0C)
    elite = hunt.cleared(run, play.world, [*small, champion], Ground(()), door)
    assert elite is not None
    assert elite.unit == 61  # its elite packs, as on every level


# --- remnants are no goal on TZ+ (agenda.py REMNANTS_LEFT; rca/2026-10-21/tz-remnants-findings.md) ---


def test_a_remnant_is_a_group_under_the_reasonable_size_with_no_leader():
    # The player, 2026-10-21 ~21:18: "kill all packs and DO NOT hunt every single enemy"
    from inventory_tracking.macros.agenda import GROUP_LINK, GROUP_MIN, remnants

    lone, pair = [(1, (0.0, 0.0))], [(2, (200.0, 0.0)), (3, (210.0, 0.0))]
    pack = [(10 + i, (400.0 + 10.0 * i, 0.0)) for i in range(GROUP_MIN)]
    guarded = [(20, (600.0, 0.0)), (21, (610.0, 0.0))]  # a champion (20) and one beside it
    assert GROUP_LINK >= 10.0
    assert remnants([*lone, *pair, *pack, *guarded], kept={20}) == {1, 2, 3}


def test_tz_plus_leaves_a_lone_striker_on_the_way_and_clears_a_pack_of_them(monkeypatch):
    # The ruling of 2026-10-19 ~21:15 ("don't waste time awaiting when mobs engage us") stays for packs: a remnant
    # striking at the party is struck when it comes in reach, never gone to
    from inventory_tracking.macros import agenda
    from inventory_tracking.macros.agenda import GROUP_MIN, PLUS

    door = Goal('Next level', (5000.0, 5300.0), ENTER, PLACE_NEAR, PRESSED, route='Andariel')
    play, hunt, run = agenda_hunt(PLUS)
    play.world = replace(play.world, player=replace(me(play.world), area=35))  # Catacombs 2: under BIG_LEVEL
    archer = replace(foe(32, 5025.0, 5000.0, txt_id=576), mode=4)
    left = hunt.cleared(run, play.world, [archer], Ground(()), door)
    assert left is not None
    assert left.unit != 32
    archers = [replace(archer, unit_id=40 + i, x=5025.0 + 5.0 * i) for i in range(GROUP_MIN)]
    goal = hunt.cleared(run, play.world, archers, Ground(()), door)
    assert goal is not None
    assert (goal.do, goal.unit, goal.clearing) == (FIGHT, 40, True)
    monkeypatch.setattr(agenda, 'REMNANTS_LEFT', False)
    play, hunt, run = agenda_hunt(PLUS)
    play.world = replace(play.world, player=replace(me(play.world), area=35))
    before = hunt.cleared(run, play.world, [archer], Ground(()), door)
    assert before is not None
    assert (before.do, before.unit) == (FIGHT, 32)


def test_a_heralds_minions_left_without_it_are_no_goal_and_with_it_are(monkeypatch):
    # 21:37:51-21:38:03 on 2026-10-21, Frigid Highlands: the Herald dead, its two Demon Rascals 26 apart were the goal
    # in turn, 11 Teleports in 12 s for one kill (JUMP_CLUSTER, take 20261021T183415Z-117)
    from inventory_tracking.macros import agenda
    from inventory_tracking.macros.agenda import PLUS
    from tests.inventory_tracking.macros.test_hunt import MINION

    play, hunt, run = agenda_hunt(PLUS)
    here = (me(play.world).x, me(play.world).y)
    rascals = [foe(70, here[0] + 26.0, here[1], MINION, txt_id=493, tier=4), foe(71, here[0] + 52.0, here[1], MINION,
               txt_id=493, tier=4)]  # fmt: skip
    left = hunt.agenda_target(run, play.world, rascals, here, frozenset(), ROOMS, None)
    assert left is None or left.unit is None  # the next room: the remnants are struck in reach only
    herald = foe(72, here[0] + 40.0, here[1], 0x08, txt_id=493, tier=4)
    target = hunt.agenda_target(run, play.world, [*rascals, herald], here, frozenset(), ROOMS, None)
    assert target is not None
    assert target.unit in {70, 72}  # the Herald's pack: the Herald first (HERALD) or its minion by it
    monkeypatch.setattr(agenda, 'REMNANTS_LEFT', False)
    play, hunt, run = agenda_hunt(PLUS)
    target = hunt.agenda_target(run, play.world, rascals, here, frozenset(), ROOMS, None)
    assert target is not None
    assert target.unit == 70


# --- a small level entered before its map is read (rca/2026-10-21/small-levels-findings.md) ---

TEMPLE, UPPER_KURAST = 96, 81  # the Forgotten Reliquary, entered from Upper Kurast at 09:09:02 on 2026-10-21
NOTHING_LEFT_END = 'nothing is left to go to on this level: no route stage, no boss known'


def temple_arrival():
    """The loop's TZ+ run posted at 10.0 on arrival in the temple, the level guide's card still Upper Kurast's."""
    from inventory_tracking.levels.model import Level
    from inventory_tracking.macros.agenda import PLUS

    play = game(area=TEMPLE)
    hunt = hunter(play, explored=())
    card = [Level(UPPER_KURAST, ROOMS, FLOOR)]
    hunt.level = lambda: card[0]
    hunt.agenda, hunt.agenda_policy = Agenda(), lambda area: PLUS
    hunt.agenda.begin('g')
    hunt.pursuit = Pursuit('pickup', 10.0, advance=False, leash=FULL, looped=True, agenda=True)
    hunt.mode = Mode(True, AGENDA, agenda=True)
    return play, hunt, card


def test_a_temple_entered_before_its_map_is_read_waits_for_the_map_and_is_explored():
    # 09:09:02.320 in, 09:09:02.734 "Level run over: nothing is left to go to" and the level done with 9 hostiles
    # alive; the card came at ~0.6 s, the run was over by then
    from inventory_tracking.levels.model import Level
    from inventory_tracking.macros.build import NoWay
    from inventory_tracking.macros.pursuit import MAP_SAID, Ended

    play, hunt, card = temple_arrival()
    run = play.run()
    play.clock.now = 10.8  # the post no longer fresh: the run's own look
    waiting = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
    assert waiting.act == NoWay(MAP_SAID)
    card[0] = Level(TEMPLE, ROOMS, FLOOR)  # the guide's poll read the temple
    play.clock.now = 11.3
    found = hunt.judge(run, play.world, [], Ground(()), in_reach=False)
    assert not isinstance(found.act, Ended)
    assert found.goal is not None
    assert found.goal.clearing  # the agenda's next room: the temple is explored


def test_a_level_whose_map_never_comes_ends_after_the_wait_and_the_switch_off_ends_at_once(monkeypatch):
    from inventory_tracking.macros import pursuit
    from inventory_tracking.macros.pursuit import MAP_WAIT, Ended

    play, hunt, _ = temple_arrival()
    run = play.run()
    play.clock.now = 10.0 + MAP_WAIT + 0.1
    assert hunt.judge(run, play.world, [], Ground(()), in_reach=False).act == Ended(NOTHING_LEFT_END)
    monkeypatch.setattr(pursuit, 'WAIT_FOR_MAP', False)  # as before 2026-10-21
    play, hunt, _ = temple_arrival()
    run = play.run()
    play.clock.now = 10.8
    assert hunt.judge(run, play.world, [], Ground(()), in_reach=False).act == Ended(NOTHING_LEFT_END)


def test_the_map_wait_holds_what_is_in_reach_and_a_level_read_with_nothing_left_ends_at_once():
    # The Worldstone Chamber's case (runner.py `_run_over`, 04:32 on 2026-10-20): its map read, nothing to go to, the
    # run ends at once as before; the agenda's repeat guard (test_runner.py) counts those ends
    from inventory_tracking.macros.build import NoWay, Step
    from inventory_tracking.macros.pursuit import MAP_SAID, MAP_WAIT, Ended, Facts, Hold, decide

    posted = Pursuit('pickup', 10.0, advance=False, leash=FULL, area=TEMPLE, looped=True, agenda=True)
    nothing = Facts(10.8, None, False, False, True, lambda: Step((1.0, 1.0), None), TEMPLE, mapped=False)
    assert decide(nothing, posted) == NoWay(MAP_SAID)
    assert decide(replace(nothing, in_reach=True), posted) == Hold()
    later = replace(nothing, now=10.0 + MAP_WAIT + 0.1)
    assert decide(later, posted) == Ended(NOTHING_LEFT_END)
    assert decide(replace(later, in_reach=True), posted) == Hold()  # still no map: what is in reach first
    assert decide(replace(nothing, mapped=True), posted) == Ended(NOTHING_LEFT_END)
    chamber = replace(posted, area=132)
    assert decide(Facts(10.8, None, False, False, True, lambda: Step((1.0, 1.0), None), 132), chamber) == Ended(
        NOTHING_LEFT_END
    )
