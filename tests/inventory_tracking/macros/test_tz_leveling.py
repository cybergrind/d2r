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
