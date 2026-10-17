"""The teleport step on a scripted level: a teleport as far as the screen shows, or a walk into a near door.

The character stands at world (5000, 5000), tile (1000, 1000), in an 8x8 room; the mark lies east.
In view (teleport.VIEW, the classic projection) a hop straight east reaches about 26 world units:
(dx + dy) * 8 / 600 must stay under 0.84 - 0.494 of the window height, the skill bar being the limit.
"""

import math
from dataclasses import replace

import pytest

from inventory_tracking.levels.model import (
    HELL_GATE,
    PORTAL,
    SEALS,
    SUPER_CHEST,
    WIRTS_BODY,
    Ground,
    Room,
    Target,
    Walkable,
    pack_cells,
    pack_tiles,
)
from inventory_tracking.macros import teleport
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.teleport import (
    NEAR_WARP,
    Way,
    approaches,
    footing,
    hop_in_view,
    landing,
    step_toward,
)
from inventory_tracking.macros.world import USED, Teleport, Thing, Warp
from tests.inventory_tracking.macros.fakes import KEYS, SLOTS, Game, player, world


HERE = Room(1, 996, 996, 8, 8)
EAST = tuple(Room(2 + i, 1004 + 8 * i, 996, 8, 8) for i in range(4))  # a corridor to the east
STAFF = Teleport(10, 20, True)


def staff(play: Game) -> Teleport:
    """The staff the character of `game` wears."""
    assert play.staff is not None
    return play.staff


def keys(_world, skills):
    return {skill: KEYS[skill] for skill in skills}


def target(point, rooms=(HERE, *EAST), *, area=109, warp=False):
    return Target(area, tuple(rooms), point, 'Next level', 'stairs', warp)


def game(staff=STAFF, **changes):
    found = Game(world(**changes))
    found.staff = staff
    return found


def test_a_mark_in_sight_is_one_teleport_onto_it():
    play = game()
    step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert math.dist((play.character.x, play.character.y), (5015.0, 5000.0)) < 0.5
    assert staff(play).charges == 9
    assert play.said[-2].startswith('Teleport toward Next level')  # then the key's own name


def test_a_far_mark_gets_a_hop_to_the_edge_of_the_screen_along_the_line():
    play = game()
    step_toward(play.run(), target((1031.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    moved = play.character.x - 5000.0
    assert 24.0 < moved < 31.0  # as far east as the view shows ground, a little north to use its shape
    assert -6.0 < play.character.y - 5000.0 <= 0.5


def test_void_wider_than_a_teleport_sends_the_hop_toward_the_bridge_room():
    bridge, far = Room(5, 1002, 1004, 8, 8), Room(6, 1010, 996, 8, 8)  # six tiles of void straight east
    play = game()
    step_toward(play.run(), target((1014.0, 1000.0), (HERE, bridge, far)), keys)
    assert play.pressed() == ['t']
    assert play.character.y > 5005.0  # south-east, toward the bridge, not straight east
    assert play.character.x > 5005.0


def test_a_door_within_reach_is_walked_into_and_the_level_changes():
    play = game()
    play.door = (1001.5, 1000.5)  # 7.9 units away
    step_toward(play.run(), target(play.door, warp=True), keys)
    assert play.pressed() == []
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.character.area == 110
    assert play.said == ['Walking into Next level, 8 away', 'Next level: there']


def test_a_doorway_drawn_above_its_tile_is_clicked_there_when_the_ground_does_not_take():
    # Worldstone Keep's stairs (host, 01:32 on 2026-10-10): the teleport landed on the warp tile and
    # the click on the ground under the character's feet moved nobody.
    play = game(player=player(x=5007.5, y=5002.5))
    play.door, play.door_above, play.hover_known = (1001.5, 1000.5), 60, False
    step_toward(play.run(), target(play.door, warp=True), keys)
    # the click on the ground moved nobody and is made again (a cast may have swallowed it), then the aim above
    assert [event[0] for event in play.keys.events] == ['click', 'click', 'click']
    assert play.character.area == 110
    assert play.said == ['Walking into Next level, 0 away', 'Next level: there']


def test_an_aim_without_the_door_under_the_pointer_is_not_clicked():
    # The tower's door in Black Marsh (host, 22:43 on 2026-10-10): three clicks on the ground beside the
    # door walked the character round the entrance for 6 s; the game's record had no tile under them.
    play = game(player=player(x=5007.5, y=5002.5))
    play.door, play.door_above = (1001.5, 1000.5), 60
    step_toward(play.run(), target(play.door, warp=True), keys)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.walks == []
    assert play.character.area == 110


def test_a_door_the_record_never_shows_is_clicked_at_every_aim_after_two_looks(caplog):
    play = game()
    play.door = (1001.5, 1000.5)
    run = play.run()
    run.hovered = lambda: (2, 7)  # the record still holds the waypoint taken in town
    with caplog.at_level('INFO'):
        step_toward(run, target(play.door, warp=True), keys)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.character.area == 110
    assert any('no door under the pointer at the aims' in r.message for r in caplog.records)


def portal_mark(point):
    return Target(109, (HERE, *EAST), point, 'Tristram', 'target', use=PORTAL)


def test_a_portal_in_reach_of_its_mark_is_clicked_on_its_picture_and_the_level_changes():
    # Stony Field (user, 2026-10-12): the step stood at the Cairn Stones and never took the portal.
    play = game()
    play.thing = Thing(77, PORTAL, 0, 5012.0, 5004.0)  # an object beside the mark, not a warp tile
    step_toward(play.run(), portal_mark((1001.0, 1000.0)), keys)
    assert play.pressed() == []
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.walks == []
    assert play.character.area == 110
    assert play.said == ['Through the portal to Tristram, 13 away', 'Tristram: there']


def test_a_portal_aim_with_something_else_under_the_pointer_is_not_clicked():
    play = game()
    play.thing, play.thing_above = Thing(77, PORTAL, 0, 5012.0, 5004.0), 75  # only the second aim is on its picture
    step_toward(play.run(), portal_mark((1001.0, 1000.0)), keys)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.walks == []
    assert play.character.area == 110


def test_a_portal_no_aim_shows_is_reported_without_a_click():
    play = game()
    play.thing, play.thing_above = Thing(77, PORTAL, 0, 5012.0, 5004.0), 300
    with pytest.raises(Abort, match='Tristram is not under the pointer'):
        step_toward(play.run(), portal_mark((1001.0, 1000.0)), keys)
    assert play.keys.events == []


def test_a_portal_far_from_the_character_is_teleported_toward_first():
    play = game()
    play.thing = Thing(77, PORTAL, 0, 5152.0, 5004.0)
    step_toward(play.run(), portal_mark((1030.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert play.character.area == 109


def test_at_a_portals_mark_with_no_portal_open_the_step_says_so():
    play = game()
    with pytest.raises(Abort, match='no portal to Tristram is open here'):
        step_toward(play.run(), portal_mark((1001.0, 1000.0)), keys)
    assert play.pressed() == []


def test_another_portal_far_from_the_mark_is_not_the_marks():
    play = game()
    play.thing = Thing(77, PORTAL, 0, 5012.0, 5004.0)  # a portal here, the mark's a screen away
    step_toward(play.run(), portal_mark((1030.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert play.character.area == 109


def body_mark(point):
    return Target(38, (HERE, *EAST), point, "Wirt's body", 'target', use=WIRTS_BODY)


def test_a_body_at_its_mark_is_clicked_until_it_shows_searched():
    play = game(area=38)
    play.thing, play.thing_above = Thing(78, WIRTS_BODY, 0, 5010.0, 5002.0), 0  # it lies on its ground point
    step_toward(play.run(), body_mark((1002.0, 1000.4)), keys)
    assert play.pressed() == []
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.thing.mode == 2
    assert play.character.area == 38
    assert play.said == ["Searching Wirt's body, 10 away", "Wirt's body: searched"]


def test_a_body_searched_already_is_not_clicked_again():
    play = game(area=38)
    play.thing, play.thing_above = Thing(78, WIRTS_BODY, 2, 5010.0, 5002.0), 0
    step_toward(play.run(), body_mark((1002.0, 1000.4)), keys)
    assert play.keys.events == []
    assert play.said == ["At Wirt's body"]


def test_the_click_that_took_a_levels_door_is_tried_first_next_time():
    for _ in range(2):
        play = game()
        play.door, play.door_above = (1001.5, 1000.5), 60
        teleport.ENTRIES = teleport.Entries(None)  # the door's spot forgotten: this is about the click alone
        step_toward(play.run(), target(play.door, warp=True), keys)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.character.area == 110


def test_a_door_whose_aim_the_logs_gave_is_clicked_there_first():
    stairs = Room(144, 996, 996, 8, 8)  # 'Act 1 - Crypt Next E': the stairs down in the Tower Cellar
    mark = Target(21, (stairs,), (1001.5, 1000.5), 'Next level', 'stairs', True)
    assert teleport.door_aims(mark)[0] == (-50, -45)
    teleport.AIMS.learn(mark, (0, -45))  # what took it last goes before what the logs gave
    assert teleport.door_aims(mark)[:2] == ((0, -45), (0, 0))


def test_a_door_the_game_shows_is_clicked_in_the_middle_of_its_own_box():
    # The tower's door in Black Marsh (the running game, 23:02 on 2026-10-10): the door unit (lvlwarp Id
    # 10, box -10, -50 to 140, 30) at (15651, 5385), the mark at (15657.5, 5387.5).
    tower = Warp(1593147781, 10, 15651.0, 5385.0)
    assert teleport.box_aim((15657.5, 5387.5), (tower,)) == (1, -82)
    assert teleport.box_aim((15657.5, 5387.5), (Warp(7, 11, 10004.0, 8003.0),)) is None  # another level's door
    assert teleport.box_aim((15657.5, 5387.5), (Warp(7, 999, 15651.0, 5385.0),)) is None  # no box known
    mark = Target(6, (HERE,), (3131.5, 1077.5), 'Forgotten Tower', 'stairs', True)
    assert teleport.door_aims(mark, (tower,))[0] == (1, -82)


def test_the_doors_own_box_is_the_first_click():
    play = game(player=player(x=5007.5, y=5002.5))
    play.door, play.door_above = (1001.5, 1000.5), 82  # only the box takes: 82 pixels above the tiles
    run = play.run()
    run.warps = lambda: (Warp(3, 10, 5001.0, 5000.0),)  # 6.5, 2.5 units from the mark, as the tower's
    step_toward(run, target(play.door, warp=True), keys)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.walks == []
    assert play.character.area == 110


def test_a_door_aim_with_a_monster_under_it_is_left_for_last():
    # The mercenary lands beside the character after a hop: a click on it is not a click on the door.
    play = game()
    play.door = (1001.5, 1000.5)
    run = play.run()
    looks = iter([(1, 77), (5, 9)])  # a monster under the first aim, the door under the next
    run.hovered = lambda: next(looks)
    step_toward(run, target(play.door, warp=True), keys)
    assert play.character.area == 110
    assert teleport.AIMS.offset(target(play.door, warp=True)) == (0.0, -45.0)  # the next aim: the first was not clicked


def test_one_click_from_where_the_character_stands_makes_that_spot_the_doors_entry():
    # Tower Cellar: the stairs took the click from 5.6 units without a step.
    play = game()
    play.door = (1001.0, 1000.0)  # world (5005, 5000), 5 from the character
    mark = target(play.door, warp=True)
    step_toward(play.run(), mark, keys)
    assert teleport.ENTRIES.offset(mark) == (-5.0, 0.0)


def test_the_way_back_is_not_walked_into():
    # Tower Cellar 5: the stairs up to level 4 are the only mark, and the step after arriving took them.
    play = game()
    back = Target(109, (HERE,), (1001.5, 1000.5), 'Tower Cellar 4', 'previous', True)
    with pytest.raises(Abort, match='back to Tower Cellar 4'):
        step_toward(play.run(), back, keys)
    assert play.keys.events == []


def test_a_door_no_click_takes_is_reported():
    play = game()
    play.door, play.door_above = (1001.5, 1000.5), 400
    with pytest.raises(Abort, match='no click took'):
        step_toward(play.run(), target(play.door, warp=True), keys)


def test_the_last_hop_before_a_door_lands_beside_it_on_the_characters_side():
    # user, 2026-10-10: a hop onto the warp tiles put the character off to a side, and the walk in went
    # around. Solid ground to the east; the door 20 units away: the landing is about APPROACH units
    # short of it, west of it, not on its tiles.
    wide = Walkable(996, 996, 16, 8, pack_tiles('1' * 128, 16))
    play = game()
    door = (1004.0, 1000.0)
    mark = Target(109, (HERE, *EAST), door, 'Next level', 'stairs', True, (wide,))
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    landed = (play.character.x, play.character.y)
    assert teleport.WARP_TILES < math.dist(landed, (5020.0, 5000.0)) < teleport.APPROACH + 1.0
    assert landed[0] < 5020.0 - teleport.WARP_TILES  # west of the door: the side the character came from
    assert abs(landed[1] - 5000.0) < 2.5  # straight west, give or take the aim scatter


def test_a_door_further_than_a_walk_is_teleported_toward():
    play = game()
    door = (1000.0 + (NEAR_WARP + 5) / 5, 1000.0)
    step_toward(play.run(), target(door, warp=True), keys)
    assert play.pressed() == ['t']


def test_a_staff_on_the_other_set_is_swapped_in_first_and_left_in_hand():
    play = game(Teleport(10, 20, False))
    step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['c', 't']
    assert play.staff == Teleport(9, 20, True)


def test_teleport_as_a_skill_needs_no_staff():
    play = game(None)
    step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert 'charges' not in play.said[-2]


@pytest.mark.parametrize(
    ('staff', 'slots', 'mark', 'message'),
    [
        (Teleport(0, 20, True), SLOTS, target((1003.0, 1000.0)), 'charges'),
        (STAFF, tuple(None if s == 54 else s for s in SLOTS), target((1003.0, 1000.0)), 'skill key'),
        (STAFF, SLOTS, target((1003.0, 1000.0), area=110), 'another level'),
        (STAFF, SLOTS, None, 'level card'),
        (STAFF, SLOTS, target((1014.0, 1000.0), (HERE,)), 'no way over the rooms'),  # the mark is off the rooms
    ],
)
def test_nothing_is_pressed_when_the_step_cannot_be_taken(staff, slots, mark, message):
    play = game(staff, slots=slots)
    with pytest.raises(Abort, match=message):
        step_toward(play.run(), mark, keys)
    assert play.keys.events == []


def test_an_open_panel_stops_the_step():
    play = game(open_panels=('inventory',))
    with pytest.raises(Abort, match='inventory is open'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)


def test_a_teleport_that_moves_nobody_is_reported():
    play = game()
    play.staff = None  # Teleport as a skill of the character's own
    play.keys.on_event = lambda event: None  # the game ignores the key
    with pytest.raises(Abort, match='did not move'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)


def test_a_key_that_casts_nothing_with_the_staff_in_hand_is_named_as_teleport_off_its_key():
    # user, 2026-10-11: a game left with the staff in hand loses Teleport's key in the next one; three
    # steps in a row "did not move" at 01:26 that night until it was bound again.
    play = game()
    assert play.staff is not None
    assert staff(play).in_hand
    play.keys.on_event = lambda event: None  # the key is bound to nothing: no charge is spent
    with pytest.raises(Abort, match='Teleport is off its key: bind it again'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t', 't']  # pressed once more before it is given up


PIT = Walkable(996, 996, 8, 8, pack_tiles('11111100' * 8, 8))  # the room's two eastern tile columns are a pit
SOLID = Walkable(996, 996, 8, 8, pack_tiles('1' * 64, 8))


def test_the_landing_stops_short_of_a_pit_the_grids_know_about(caplog):
    play = game()
    mark = Target(109, (HERE, *EAST), (1002.4, 1000.0), 'Next level', 'stairs', False, (PIT,))  # in the pit
    with caplog.at_level('INFO'):
        step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    assert 5005.0 < play.character.x < 5009.5  # before the pit at x = 5010, a unit of margin kept
    [line] = [r.message for r in caplog.records if 'teleport aimed at' in r.message]
    assert 'off the way, footing True, 1 grids' in line
    assert 'landed at' in line


def test_a_chasm_in_the_way_is_crossed_where_the_view_shows_ground_beyond_it():
    beyond = Room(9, 1004, 996, 8, 8)
    chasm = Walkable(1004, 996, 8, 8, pack_tiles('01111111' * 8, 8))  # a tile column of nothing, then floor
    play = game()
    mark = Target(109, (HERE, beyond), (1011.0, 1000.0), 'Next level', 'stairs', False, (SOLID, chasm))
    step_toward(play.run(), mark, keys)
    assert play.character.x > 5025.5  # over the chasm (x 5020-5025), on the floor beyond, a unit in


def test_known_solid_ground_lands_on_the_mark_and_logs_the_miss(caplog):
    play = game()
    mark = Target(109, (HERE, *EAST), (1003.0, 1000.0), 'Next level', 'stairs', False, (SOLID,))
    with caplog.at_level('INFO'):
        step_toward(play.run(), mark, keys)
    [line] = [r.message for r in caplog.records if 'teleport aimed at' in r.message]
    assert 'aimed at (5015.0, 5000.0), 15.0 from (5000.0, 5000.0),' in line
    assert 'off the way, footing True, 1 grids' in line
    assert ', off by 0.' in line  # the fake lands where the pointer points, give or take the scatter


def test_footing_needs_the_neighbours_too_and_is_unknown_off_the_grids():
    ground = Ground((PIT,))
    assert footing(ground, (1000.0, 1000.0)) is True
    assert footing(ground, (1001.9, 1000.0)) is False  # a unit from the pit's edge at x = 1002
    assert footing(ground, (1002.5, 1000.0)) is False
    assert footing(ground, (1010.0, 1000.0)) is None


def test_a_character_on_a_tile_whose_centre_is_a_pit_still_has_a_way():
    # The character stands on the walkable western edge of a tile whose centre is pit (River of Flame
    # lava edges, host 20:09 on 2026-10-09): the way starts from the landable tiles one hop away.
    rows = [
        ''.join('0' if 20 <= col < 25 and 20 <= row < 25 and (col, row) != (20, 22) else '1' for col in range(40))
        for row in range(40)
    ]
    edge = Walkable(996, 996, 8, 8, pack_cells(''.join(rows)))  # tile (1000, 1000) is pit but for one sub-tile
    play = game()
    play.world = replace(play.world, player=replace(play.character, x=5000.4, y=5002.5))  # on that sub-tile
    mark = Target(109, (HERE, *EAST), (1003.0, 1000.0), 'Next level', 'stairs', False, (edge,))
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']


def test_the_potential_plans_no_hop_the_view_cannot_show():
    # Host, 19:19 on 2026-10-10, Catacombs 1: the only way on was a landing 21 units straight down the
    # screen, below where the view ends at the skill bar; the potential counted it as one hop and twenty
    # seek steps in a row found "no footing in view".
    assert hop_in_view(-3, -3)  # 21 units straight up the screen
    assert not hop_in_view(3, 3)  # the same straight down
    assert hop_in_view(2, 2)
    assert hop_in_view(2, -3)  # and to a side
    # Two rooms a gap apart, the second straight down the screen from the first: no way from the first
    # to a mark in the second, and a way back up from the second.
    upper, lower = Room(1, 1000, 1000, 2, 2), Room(2, 1004, 1004, 2, 2)
    down = Way(Target(109, (upper, lower), (1004.5, 1004.5), 'below', 'mark', False, ()))
    up = Way(Target(109, (upper, lower), (1001.5, 1001.5), 'above', 'mark', False, ()))
    assert down.from_here((1001.5, 1001.5)) == math.inf
    assert up.from_here((1004.5, 1004.5)) < math.inf


def test_a_spot_beside_the_door_the_way_does_not_count_is_not_the_landing():
    # Host, 19:29 on 2026-10-10, Catacombs 1: the "beside the door" spot nearest the character had
    # footing but lay on a tile whose centre was wall, so the way gave it no cost; the landing came
    # out as no gain and sixteen teleport steps in a row stopped 16 units from the door.
    door = Target(109, (HERE, *EAST), (1003.5, 1000.5), 'Next level', 'stairs', True, ())
    way = Way(door)
    nearest = min(approaches(door), key=lambda spot: math.dist(spot, (1000.0, 1000.0)))
    real = way.to_go
    way.to_go = lambda point: math.inf if math.dist(point, nearest) < 0.3 else real(point)
    found = landing(door, player(), way, 2560 / 1418)
    assert found is not None
    spot, gain = found
    assert math.dist(spot, nearest) >= 0.3
    assert gain > 0.5


def test_a_pointer_found_off_the_aim_is_aimed_again_before_the_key(caplog):
    play = game()
    hand = {'drags': 2, 'reads_since_move': 0}  # the hand drags the pointer off right after each of two moves
    real_move, real_pointer = play.keys.move_pointer, play.keys.pointer

    def move_pointer(x, y):
        hand['reads_since_move'] = 0
        return real_move(x, y)

    def pointer():
        first = hand['reads_since_move'] == 0
        hand['reads_since_move'] += 1
        if first and hand['drags']:
            hand['drags'] -= 1
            return (play.keys.at[0] + 120, play.keys.at[1])
        return real_pointer()

    play.keys.move_pointer, play.keys.pointer = move_pointer, pointer
    with caplog.at_level('INFO'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert sum('aiming again' in r.message for r in caplog.records) == 2


def test_a_swipe_of_the_hand_across_the_screen_does_not_stop_the_step(caplog):
    # Two steps stopped "the mouse was moved" with the pointer 600 and 870 pixels off the aim (the runs
    # of 18:01 and 18:05 on 2026-10-10): the aim is made again instead.
    play = game()
    hand = {'swipes': 1, 'reads_since_move': 1}  # the swipe comes right after the macro's own move
    real_move, real_pointer = play.keys.move_pointer, play.keys.pointer

    def move_pointer(x, y):
        hand['reads_since_move'] = 0
        return real_move(x, y)

    def pointer():
        first = hand['reads_since_move'] == 0
        hand['reads_since_move'] += 1
        if first and hand['swipes']:
            hand['swipes'] -= 1
            play.keys.at = (play.keys.at[0] + 870, play.keys.at[1] - 150)  # and it stays there
        return real_pointer()

    play.keys.move_pointer, play.keys.pointer = move_pointer, pointer
    with caplog.at_level('INFO'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert sum('aiming again' in r.message for r in caplog.records) == 1


def test_a_hand_that_keeps_sweeping_the_mouse_is_beaten_by_a_jump_of_the_pointer(caplog):
    # Two seek steps stopped "the mouse is being moved" after three aims in 0.4 s (host, 20:57 and 20:58
    # on 2026-10-10): the hand carries the pointer off during every pause of a move. The last try has none.
    play = game()
    sleep = play.clock.sleep

    def sweeping(seconds):
        play.keys.at = (play.keys.at[0] + 200, play.keys.at[1] + 40)  # the hand, whenever the macro waits
        sleep(seconds)

    play.clock.sleep = sweeping
    with caplog.at_level('INFO'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert sum('aiming again' in r.message for r in caplog.records) == 2


# --- the door's own spot (user, 2026-10-10: the last hop left a walk round the stairs) ---


def walking_game(door, entry, *, after=(0.6, 0.9)):
    """A game whose door walks the clicked character to `entry` (world units) and then changes the level."""
    play = game()
    play.hover_known = False  # the walk is timed from the first click
    start = play.clock.now

    def arrive():
        play.world = replace(play.world, player=replace(play.character, x=entry[0], y=entry[1]))

    def change():
        play.world = replace(play.world, player=replace(play.character, area=110))

    play.arrivals += [(start + after[0], arrive), (start + after[1], change)]
    return play


def test_a_walk_into_a_door_is_logged_and_where_the_level_changed_is_remembered(caplog):
    door = (1001.5, 1000.5)  # the mark, at world (5007.5, 5002.5)
    play = walking_game(door, (5007.5, 5005.5))
    mark = target(door, warp=True)
    with caplog.at_level('INFO'):
        step_toward(play.run(), mark, keys)
    assert teleport.ENTRIES.offset(mark) == (0.0, 3.0)
    lines = [r.message for r in caplog.records if r.message.startswith('Macro: door')]
    assert lines[0] == (
        'Macro: door Next level marked at (5007.5, 5002.5); the character at (5000.0, 5000.0), 7.9 from the mark; '
        'entry not known yet'
    )
    assert lines[1].startswith('Macro: door Next level: in after ')
    assert ' from (5000.0, 5000.0) to (5007.5, 5005.5); ' in lines[1]  # after the seconds and the units walked
    assert lines[1].endswith('the entry at +0.0, +3.0 from the mark, 3.0 away (remembered)')


def test_a_level_change_far_from_the_mark_teaches_nothing():
    door = (1001.5, 1000.5)
    play = walking_game(door, (5000.0, 5000.0))  # the level changed where the character stood, 7.9 off
    mark = target(door, warp=True)
    step_toward(play.run(), mark, keys)
    assert teleport.ENTRIES.offset(mark) is None


def test_a_remembered_entry_is_hopped_onto_and_the_door_clicked_from_there():
    # The stairs' mark sits in a block of walls; the spot the game walks to is 3 units south of it.
    door = (1003.0, 1000.0)  # world (5015, 5000): 15 away, a walk by the old rule would not start, a hop would
    mark = target(door, warp=True)
    teleport.ENTRIES.learn(mark, (0.0, 3.0))
    play = game()
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    landed = (play.character.x, play.character.y)
    assert math.dist(landed, (5015.0, 5003.0)) < 1.5  # on the door's spot, inside WARP_TILES of the mark
    play.door = door
    step_toward(play.run(), mark, keys)  # from the spot: the click, no second hop
    assert play.pressed() == ['t']
    assert play.character.area == 110


def test_a_door_within_a_walk_but_off_its_remembered_spot_is_hopped_onto_first():
    door = (1001.5, 1000.5)  # 7.9 away: walked into before the spot was known
    mark = target(door, warp=True)
    teleport.ENTRIES.learn(mark, (0.0, 3.0))
    play = game()
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    assert math.dist((play.character.x, play.character.y), (5007.5, 5005.5)) < 1.5


def test_a_remembered_spot_a_few_steps_off_over_open_ground_is_walked_to_by_the_click():
    # user, 2026-10-10: "we have jumped twice around the entrance": a hop beside the door, a hop onto its
    # spot 6 units on, then the click. The click walks those steps itself.
    door = (1001.3, 1000.3)  # world (5006.5, 5001.5); its spot 3 south of it, 7.9 from the character
    mark = replace(target(door, warp=True), ground=(SOLID,))
    teleport.ENTRIES.learn(mark, (0.0, 3.0))
    play = game()
    play.door = door
    step_toward(play.run(), mark, keys)
    assert play.pressed() == []  # no hop
    assert play.character.area == 110


def test_a_remembered_spot_behind_a_wall_is_still_hopped_onto():
    door = (1001.3, 1000.3)
    rows = ''.join('0' if 23 <= col <= 24 else '1' for col in range(40)) * 40  # a wall at world x 5003-5004
    mark = replace(target(door, warp=True), ground=(Walkable(996, 996, 8, 8, pack_cells(rows)),))
    teleport.ENTRIES.learn(mark, (0.0, 3.0))
    play = game()
    step_toward(play.run(), mark, keys)
    assert play.pressed() == ['t']
    assert math.dist((play.character.x, play.character.y), (5006.5, 5004.5)) < 1.5


def test_door_entries_are_kept_in_a_file_across_games(tmp_path):
    mark = target((1001.5, 1000.5), warp=True, area=36)
    first = teleport.Entries(tmp_path / 'macros' / 'door-entries.json')
    first.learn(mark, (0.04, 2.96))
    again = teleport.Entries(tmp_path / 'macros' / 'door-entries.json')
    assert again.offset(mark) == (0.0, 3.0)
    # The same stairs preset on another level has the same spot; another preset (another orientation) has none.
    assert again.offset(target((1001.5, 1000.5), warp=True, area=37)) == (0.0, 3.0)
    # Another preset on the level it was learned on falls back on the level's spot (the Catacombs' stairs
    # presets share one shape); another preset on another level has none.
    assert again.offset(target((1005.5, 1000.5), warp=True, area=36)) == (0.0, 3.0)
    assert again.offset(target((1005.5, 1000.5), warp=True, area=38)) is None
    assert teleport.Entries.key(target((1001.5, 1000.5), warp=True)) == 'preset 1:stairs'
    assert teleport.Entries.key(target((900.0, 900.0), warp=True, area=36)) == 'area 36:stairs'  # on no room
    (tmp_path / 'broken.json').write_text('{')
    assert teleport.Entries(tmp_path / 'broken.json').offset(mark) is None


def test_the_card_of_the_level_just_left_is_waited_out():
    # 15 of 116 logged exits: the step asked for on arrival stopped with "the level card is for another level".
    from inventory_tracking.macros.teleport import CARD_SECONDS, card_for

    play = game(area=36)
    run, clock = play.run(), play.clock
    old, new = target((1003.0, 1000.0), area=35), target((1003.0, 1000.0), area=36)
    assert card_for(run, lambda: new if clock.now >= 0.37 else old) is new
    assert 0.37 <= clock.now < 0.5
    # Tower Cellar 1, 21:36:39 on 2026-10-11: the press on arrival waited 580 ms for the service's
    # half-second look at the level. The step asks for that look, once, and only when it has to wait.
    asked = []
    run.hurry = lambda: asked.append(clock.now)
    assert card_for(run, lambda: new) is new
    assert asked == []
    started = clock.now
    assert card_for(run, lambda: new if asked and clock.now >= asked[0] + 0.1 else old) is new
    assert asked == [started]
    clock.now = 0.0
    assert card_for(run, lambda: old) is old  # never read: the step says so, CARD_SECONDS later
    assert CARD_SECONDS <= clock.now < CARD_SECONDS + 0.1
    assert card_for(run, None) is None


def test_a_door_click_a_cast_swallowed_is_made_again_at_the_same_aim():
    # Tower Cellar (host, 23:35 on 2026-10-10): attack mode's strike 0.7 s before the click on the stairs;
    # the character stood where it was, two aims off the door followed, 4.77 s in all.
    play = game()
    play.door, play.swallowed_clicks = (1001.0, 1000.0), 1
    began = play.clock.now
    step_toward(play.run(), target(play.door, warp=True), keys)
    assert play.character.area == 110
    assert [event[0] for event in play.keys.events] == ['click', 'click']
    assert play.walks == []
    assert play.clock.now - began < 1.0


def test_a_walk_under_way_when_the_hop_begins_is_not_its_landing():
    # "landed ..., off by 24" 0.2 s after the key (Tower, 2026-10-10; Black Marsh, 2026-10-11): the
    # character was walking when the hop began, and the walk's movement was taken for the landing.
    from inventory_tracking.macros.teleport import landed_from

    since = player(x=5000.0, y=5000.0)
    aim = (5025.0, 5000.0)
    assert not landed_from(replace(since, x=5003.0, mode=3), since, aim)  # still running: the walk
    assert not landed_from(replace(since, x=5001.0, mode=1), since, aim)  # has not moved
    assert landed_from(replace(since, x=5024.5, mode=1), since, aim)  # stands somewhere else: landed
    assert landed_from(replace(since, x=5024.5, mode=3), since, aim)  # at the aim, whatever its mode
    assert landed_from(replace(since, area=since.area + 1), since, aim)


def test_a_press_the_game_drops_is_pressed_again_and_the_lost_key_is_not_named_after_a_hop_landed():
    # Worldstone Keep 3, 03:12:00 on 2026-10-11: the 21st hop of a chain cast nothing and was named
    # as the lost key; the same aim landed half a second later.
    play = game()
    react, dropped = play.keys.on_event, [1]
    play.keys.on_event = lambda event: dropped.pop() if event == ('key', 't') and dropped else react(event)
    step_toward(play.run(), target((1040.0, 1000.0)), keys)
    assert play.pressed() == ['t', 't']  # the first press never reached the game, the second landed
    assert play.character.x > 5000.0

    play.keys.on_event = lambda event: None
    with pytest.raises(Abort, match='took neither of two presses'):
        step_toward(play.run(), target((1040.0, 1000.0)), keys)


def test_a_hop_aimed_beside_the_skill_bar_that_moves_nothing_is_judged_like_any_other(corners):
    # The corners are confirmed in the game: a failed hop there is a lost key or the like, not a reason
    # to stop aiming there.
    from inventory_tracking.macros import view

    play = game()
    play.keys.on_event = lambda event: None  # the game takes no cast
    mark = target((1005.5, 1000.5))  # 5.5 tiles down and right: only a corner shows that
    with pytest.raises(Abort, match=r'Teleport is off its key|did not move|took neither'):
        step_toward(play.run(), mark, keys)
    assert view.CORNERS == [True]


def test_a_far_way_failure_gives_the_target_to_the_near_way_for_a_while_only():
    # For the target, wherever the character then stands: the two potentials do not agree on which way
    # is nearer, and a hop by each in turn could go back and forth.
    from inventory_tracking.macros import teleport

    mark, other = (3, 1010, 1000), (3, 1040, 1000)
    teleport.ban_far(mark, 100.0)
    assert teleport.far_banned(mark, 100.0 + teleport.FAR_DISTRUST - 1)
    assert not teleport.far_banned(other, 101.0)
    assert not teleport.far_banned(mark, 100.0 + teleport.FAR_DISTRUST)
    assert mark not in teleport.FAR_FAILED
    teleport.ban_far(mark, 200.0)
    teleport.ban_far(other, 240.0)  # adding prunes what has expired
    assert list(teleport.FAR_FAILED) == [other]


def test_a_hop_whose_landing_is_where_the_character_stands_is_not_made(monkeypatch):
    # Beside Nihlathak, 12:25:45 on 2026-10-11: one press more than the way needed. The landing came
    # out 0.7 units from the character (7.8 off the way, as the way counts its cells); the key spent a
    # charge and the step waited 2.2 s for a move, with attack mode held back behind it.
    monkeypatch.setattr(teleport, 'landing', lambda target, player, way, aspect: ((1000.1, 1000.1), 1.5))
    play = game()
    step_toward(play.run(), target((1000.1, 1000.1)), keys)
    assert play.pressed() == []
    assert staff(play).charges == 10
    assert play.said[-1] == 'At Next level'


def test_beside_a_spot_that_is_not_a_door_no_hop_is_made():
    # 12:56:41 on 2026-10-11: a press more than the way needed, 3.5 units from Nihlathak's spot with
    # him standing on it. The hop spent a charge and moved nothing; the step waited 2.3 s and stopped.
    play = game()
    step_toward(play.run(), target((1000.5, 1000.5)), keys)
    assert play.pressed() == []
    assert staff(play).charges == 10
    assert play.said[-1] == 'At Next level'


def test_a_spot_further_off_is_still_hopped_to():
    play = game()
    step_toward(play.run(), target((1002.0, 1000.0)), keys)
    assert play.pressed() == ['t']


def test_a_short_hop_onto_a_taken_spot_that_moves_nobody_ends_the_step_at_once():
    # 12:46:08 on 2026-10-11: 7.6 units from Nihlathak's spot the hop onto it left the character where
    # it stood, and the fight began 0.76 s later.
    play = game()

    def taken(event):
        if event == ('key', 't'):
            play.staff = replace(staff(play), charges=staff(play).charges - 1)  # cast, and nowhere to land

    play.keys.on_event = taken
    began = play.clock.now
    step_toward(play.run(), target((1001.5, 1000.0)), keys)
    assert play.said[-1] == 'At Next level'
    assert play.clock.now - began < 1.0


def test_a_room_to_explore_one_tile_off_is_still_hopped_into():
    # Halls of Vaught, 15:10:20 on 2026-10-11: one tile short of an unexplored room the step said "the
    # character is beside it" 17 times and the room was never seen.
    play = game()
    room = Target(109, (HERE, *EAST), (1001.0, 1000.0), 'an unexplored room', 'explore', False)
    step_toward(play.run(), room, keys)
    assert play.pressed() == ['t']


def test_with_the_staff_empty_the_teleport_step_goes_the_way_it_is_given_instead():
    # user, 2026-10-11: "use warp if we have 0 charges"
    play = game(Teleport(0, 20, True))
    went = []
    step_toward(play.run(), target((1003.0, 1000.0)), keys, went.append)
    assert [mark.label for mark in went] == ['Next level']
    assert play.pressed() == []


def test_a_hop_is_planned_from_where_a_walk_under_way_ends():
    # Halls of Death's Calling, 12:32:17 on 2026-10-11: the step began while the sweep's walk was going.
    # The walk's end counted as the hop's landing, and every hop after was aimed from the place before
    # its own: twelve of sixteen landed 6 to 26 units off, two of them the last ones at the door.
    play = game()
    walking = replace(play.character, mode=3)
    play.world = replace(play.world, player=walking)
    stopped = replace(walking, x=5010.0, y=5000.0, mode=1)
    play.arrivals.append((0.2, lambda: setattr(play, 'world', replace(play.world, player=stopped))))
    run = play.run()
    assert teleport.settled(run, walking) == stopped


def test_a_hop_does_not_wait_long_for_a_character_the_player_keeps_running():
    play = game()
    running = replace(play.character, mode=3)
    play.world = replace(play.world, player=running)
    run = play.run()
    started = run.clock()
    assert teleport.settled(run, running) == running
    assert run.clock() - started <= teleport.SETTLE_SECONDS + 0.1


def test_the_next_hop_is_planned_from_a_fresh_landing_without_waiting_for_the_casts_end():
    # 2026-10-11, 3,300 hops: the character moves 283 ms after the key and the cast ends at 388 ms, and
    # the next key went down 567 ms after the one before, 180 ms of it the wait for the cast's end
    # before the landing was chosen and the pointer moved. The key waits for the end by itself.
    play = game()
    step_toward(play.run(), target((1003.0, 1000.0)), keys)
    ((x, y, _at),) = teleport.LANDING
    casting = replace(play.character, x=x, y=y, mode=10)
    play.world = replace(play.world, player=casting)
    play.acting_until = None  # the cast goes on: nothing ends it here
    run = play.run()
    started = run.clock()
    assert teleport.settled(run, casting) == casting
    assert run.clock() == started


def test_a_landing_that_is_old_or_not_where_the_character_is_does_not_stand_for_its_place():
    play = game()
    casting = replace(play.character, mode=10, right_skill=54)  # a Teleport that has not landed
    free = replace(casting, mode=1)
    for place in ((casting.x + 5.0, casting.y, 0.0), (casting.x, casting.y, -1.0)):
        play.world = replace(play.world, player=casting)
        play.arrivals.append((play.clock.now + 0.2, lambda: setattr(play, 'world', replace(play.world, player=free))))
        teleport.LANDING[:] = [(place[0], place[1], play.clock.now + place[2])]
        run = play.run()
        started = run.clock()
        assert teleport.settled(run, casting) == free
        assert run.clock() - started >= 0.2


def test_the_teleport_keys_pointer_is_put_in_one_step_with_a_few_milliseconds_before_the_key():
    # user, 2026-10-12: the press is the player's own, and the hop is to follow at once; the pointer's
    # path and the pause after it took 70 to 125 ms of every hop (13 queued hops, 21:35 on 2026-10-11).
    play = game()
    moves, slept = [], []
    real_move, sleep = play.keys.move_pointer, play.clock.sleep

    def move_pointer(x, y):
        moves.append((x, y, play.clock.now))
        return real_move(x, y)

    def sleeping(seconds):
        slept.append((play.clock.now, seconds))
        sleep(seconds)

    play.keys.move_pointer, play.clock.sleep = move_pointer, sleeping
    run = play.run()
    marks = {}

    def mark(name: str) -> None:
        marks.setdefault(name, play.clock.now)

    run.actuator.mark = mark
    step_toward(run, target((1003.0, 1000.0)), keys)
    assert play.pressed() == ['t']
    assert len(moves) == 1
    assert marks['first_key'] - marks['first_move'] <= 0.02


def test_a_hop_looks_at_the_game_without_its_monsters_but_for_the_warp_it_asks():
    # 22:11 on 2026-10-11: a teleport step looked at the game about six times before its key, and every
    # look walked all the monsters: 54 to 96 ms from the press to the key with nothing else in the way.
    play = game()
    run = play.run()
    looks, read = [], run.read

    def look():
        looks.append(run.light > 0)
        return read()

    run.read = look
    asked = []

    def warp(target, player, spot):
        asked.append(run.light)
        run.world()  # a Blade Warp looks for a clear line: it needs the monsters
        return False

    step_toward(run, target((1003.0, 1000.0)), keys, None, warp)
    assert play.pressed() == ['t']
    assert asked == [0]
    assert looks.count(False) == 1
    assert len(looks) > 3
    assert run.light == 0


def casting_game(keeps, cast_left=0.2):
    """A game whose character is in a cast for `cast_left` more seconds, and what it does with a key then."""
    play = game()
    play.keeps_keys = keeps
    play.world = replace(play.world, player=replace(play.character, mode=7))
    play.acting_until = play.clock.now + cast_left
    taps, press = [], play.keys.press

    def pressing(key: int) -> bool:
        if key == play.keys.names['t']:
            taps.append(play.clock.now)
        return press(key)

    play.keys.press = pressing
    return play, taps


def test_the_teleport_key_is_pressed_during_the_cast_before_and_the_game_casts_it_at_its_end():
    # user, 2026-10-12: by hand the key feels instant. The client keeps a Quick Cast key that comes
    # during a cast and casts it on the first free frame (its code, read that day); the macro waited to
    # see the cast's end and tapped then, 214 to 290 ms from press to key for a third of the presses.
    play, taps = casting_game(keeps=True)
    over = play.acting_until
    assert over is not None
    step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert len(taps) == 1
    assert taps[0] < over - 0.1  # at once: not at the cast's end
    assert play.hops_cast_at == [pytest.approx(over, abs=0.02)]
    assert math.dist((play.character.x, play.character.y), (5015.0, 5000.0)) < 3


def test_a_teleport_key_the_game_did_not_keep_is_pressed_again_when_the_cast_is_over(caplog):
    # The client drops a press under 160 ms after the cast before began while its entry is held, and a third one.
    play, taps = casting_game(keeps=False)
    over = play.acting_until
    assert over is not None
    with caplog.at_level('INFO'):
        step_toward(play.run(), target((1003.0, 1000.0)), keys)
    assert len(taps) == 2
    assert taps[0] < over - 0.1
    assert over <= taps[1] <= over + 0.2
    assert 'did not keep the Teleport key' in caplog.text
    assert play.hops_cast_at == []
    assert math.dist((play.character.x, play.character.y), (5015.0, 5000.0)) < 3


def test_a_hop_is_planned_during_a_cast_that_takes_the_character_nowhere():
    # A strike of attack mode: the character stands where the hop will start; the key waits for nothing.
    play = game()
    striking = replace(play.character, mode=10, right_skill=388)
    play.world = replace(play.world, player=striking)
    run = play.run()
    started = run.clock()
    assert teleport.settled(run, striking) == striking
    assert run.clock() == started


def placed(kind, label, point=(1002.0, 1000.4)):
    return Target(109, (HERE, *EAST), point, label, 'target', use=kind)


@pytest.mark.parametrize(
    ('kind', 'label', 'said'),
    [
        (SUPER_CHEST, 'Super chest', ['Opening Super chest, 10 away', 'Super chest: opened']),
        (SEALS[4], 'Vizier seal 1', ['Opening Vizier seal 1, 10 away', 'Vizier seal 1: open']),
    ],
)
def test_a_chest_or_a_seal_at_its_mark_is_clicked_until_it_shows_operated(kind, label, said):
    play = game()
    play.thing, play.thing_above = Thing(78, kind, 0, 5010.0, 5002.0), 10
    step_toward(play.run(), placed(kind, label), keys)
    assert [event[0] for event in play.keys.events] == ['click']
    assert play.thing.mode == 2
    assert play.said == said


def test_a_chest_far_from_the_character_is_hopped_toward_first():
    play = game()
    play.thing = Thing(78, SUPER_CHEST, 0, 5150.0, 5002.0)
    step_toward(play.run(), placed(SUPER_CHEST, 'Super chest', (1030.0, 1000.4)), keys)
    assert play.pressed() == ['t']
    assert play.thing.mode == 0


def test_the_red_portal_of_the_durance_is_gone_through_like_the_one_to_tristram():
    play = game()
    play.thing, play.thing_above = Thing(78, HELL_GATE, 2, 5010.0, 5002.0), 40
    play.next_area = 103
    step_toward(play.run(), placed(HELL_GATE, 'Red portal'), keys)
    assert play.character.area == 103
    assert play.said[-1] == 'Red portal: there'


def test_the_game_is_asked_for_every_object_the_step_clicks():
    # Every class a mark's `Use` may click, not the mark's own id: Lower Kurast's camp mark is 1000, a class no object
    # has, and the run read 1000 and never the chest at it (rca/2026-10-16/loop-first-game-findings.md §1).
    assert all(teleport.classes(use) <= USED for use in teleport.USES)


def test_at_an_empty_chest_mark_the_step_tells_the_route_instead_of_stopping():
    # rca/2026-10-16/loop-first-game-findings.md: an empty mark counts as done (the player, 2026-10-16)
    from inventory_tracking.levels.model import UNIQUE_CHEST

    play = game()
    chest = Target(109, (HERE, *EAST), (1000.0, 1000.0), 'Super chests', 'target', use=UNIQUE_CHEST)
    told = []

    step_toward(play.run(), chest, keys, empty=lambda target: told.append(target.label) or True)

    assert told == ['Super chests']
    assert play.keys.events == []
    with pytest.raises(Abort, match='Super chests is not here'):  # a route that has no use for it: said, as before
        step_toward(play.run(), chest, keys, empty=lambda target: False)


def test_a_monster_seen_on_the_object_is_told_in_the_way_when_the_acts_time_runs_out():
    # 21:16:22 on 2026-10-17: two aims at a chest had a monster under them, then the act's priced time ran out; four
    # tries in 6.5 s until the monster walked off. Told as `Covered`, the hunt fights it first (hunt.py `blocked`)
    from inventory_tracking.levels.model import UNIQUE_CHEST
    from inventory_tracking.macros.teleport import EXPIRED, Covered, use_thing

    play = game()
    run = play.run()
    me = run.world().player
    assert me is not None
    chest = Target(109, (HERE, *EAST), (me.x / 5 + 1, me.y / 5), 'Super chests', 'target', use=UNIQUE_CHEST)
    thing = Thing(9, 181, 0, me.x + 5.0, me.y)
    looks = []

    def hovered():
        looks.append(1)
        if len(looks) == 1:
            return (1, 777)  # a monster under the first aim
        raise Abort(f'{EXPIRED}: look again before continuing')

    run.hovered = hovered
    with pytest.raises(Covered) as stop:
        use_thing(run, chest, me, thing, 16 / 9)
    assert stop.value.units == {777}
    looks.clear()
    run.hovered = lambda: (_ for _ in ()).throw(Abort(f'{EXPIRED}: look again before continuing'))
    with pytest.raises(Abort) as plain:  # nothing seen on it: the stop as it was
        use_thing(run, chest, me, thing, 16 / 9)
    assert not isinstance(plain.value, Covered)
