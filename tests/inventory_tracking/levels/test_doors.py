"""Doors read closed that something stood inside (levels/doors.py PASSED_OPEN, rca/2026-10-23/jumps-findings.md fix A).

The places below are from the takes of 2026-10-22/23: the TombDoorRight 2796749121 of take 20261023T113952Z-57 (7 x 1
at (15201, 8100)) that pack members walked through at mode 0, and the TombDoorRight 1609370811 of take
20261022T234119Z-68 that three monsters pressed against at mode 0 for 30 frames (offsets 0.58-1.0 off its line) and
never crossed.
"""

from dataclasses import replace

import pytest

from inventory_tracking.levels import doors as module
from inventory_tracking.levels.doors import Door, PassedDoors
from inventory_tracking.levels.model import Ground
from inventory_tracking.macros.sight import clear_shot


TOMB_DOOR_RIGHT = 92  # objects.txt, 7 x 1 (data/doors.json)
HALLS = ('Halls 57', 692138421, 57)  # (game name, character unit, level)
SHUT = Door(2796749121, TOMB_DOOR_RIGHT, module.CLOSED_MODE, 15201.0, 8100.0)
IN_THE_DOORWAY = (15203.5, 8099.94)  # the Returned 407027519 at 14:40:12.918
PRESSED = [(15203.5, 8099.42), (15199.0, 8099.0), (15204.0, 8101.0)]  # in the slack, up to the footprint's edge
NORTH, SOUTH = (15197.5, 8089.5), (15202.5, 8115.5)  # the character at 14:40:39.06 and a member past the door


@pytest.fixture(autouse=True)
def passed_open(monkeypatch):
    """The switch on: these tests are of it (each that wants it off says so)."""
    monkeypatch.setattr(module, 'PASSED_OPEN', True)


def test_a_door_nobody_stood_inside_still_blocks_the_shot() -> None:
    passed = PassedDoors()
    seen = passed.seen(HALLS, [SHUT], [NORTH, SOUTH, *PRESSED])
    assert seen == (SHUT,)
    assert seen[0].closed
    assert not clear_shot(Ground(()), NORTH, SOUTH, seen)  # the Catacombs ruling of 2026-10-10


def test_a_door_a_hostile_stood_inside_is_open_for_the_rest_of_the_level() -> None:
    passed = PassedDoors()
    (door,) = passed.seen(HALLS, [SHUT], [NORTH, IN_THE_DOORWAY])
    assert door.passed
    assert not door.closed
    assert not door.blocks(IN_THE_DOORWAY)
    assert door.mode == module.CLOSED_MODE  # the game's mode, as read
    (later,) = passed.seen(HALLS, [SHUT], [NORTH])  # nobody in the doorway any more
    assert later.passed
    assert clear_shot(Ground(()), NORTH, SOUTH, (later,))


def test_the_character_inside_passes_the_door_as_a_hostile_does() -> None:
    passed = PassedDoors()
    (door,) = passed.seen(HALLS, [SHUT], [(15200.0, 8100.2)])
    assert door.passed


def test_another_door_is_not_passed_by_one_that_was() -> None:
    other = Door(1609370811, TOMB_DOOR_RIGHT, module.CLOSED_MODE, 15301.0, 8100.0)
    passed = PassedDoors()
    seen = passed.seen(HALLS, [SHUT, other], [IN_THE_DOORWAY])
    assert [door.passed for door in seen] == [True, False]


@pytest.mark.parametrize(
    'level',
    [('Halls 57', 692138421, 58), ('Halls 58', 692138421, 57), ('Halls 57', 1, 57)],
    ids=['another level', 'another game', 'another character'],
)
def test_the_memory_is_the_level_s_and_the_game_s(level) -> None:
    passed = PassedDoors()
    passed.seen(HALLS, [SHUT], [IN_THE_DOORWAY])
    assert passed.seen(level, [SHUT], [NORTH]) == (SHUT,)
    assert passed.seen(HALLS, [SHUT], [NORTH]) == (SHUT,)  # back on the level: forgotten, as a new level is


def test_forget_starts_afresh() -> None:
    passed = PassedDoors()
    passed.seen(HALLS, [SHUT], [IN_THE_DOORWAY])
    passed.forget()
    assert passed.seen(HALLS, [SHUT], [NORTH]) == (SHUT,)


@pytest.mark.parametrize('mode', [1, 2])
def test_a_door_read_opening_or_opened_is_as_read(mode) -> None:
    opened = Door(SHUT.unit_id, SHUT.txt_id, mode, SHUT.x, SHUT.y)
    passed = PassedDoors()
    assert passed.seen(HALLS, [opened], [IN_THE_DOORWAY]) == (opened,)
    assert not opened.closed
    passed.seen(HALLS, [SHUT], [IN_THE_DOORWAY])
    assert passed.seen(HALLS, [opened], [NORTH]) == (opened,)  # the macro opened it after: the game's read


def test_the_switch_off_reads_every_door_as_today(monkeypatch) -> None:
    monkeypatch.setattr(module, 'PASSED_OPEN', False)
    passed = PassedDoors()
    seen = passed.seen(HALLS, [SHUT], [IN_THE_DOORWAY])
    assert seen == (SHUT,)
    assert seen[0].closed
    assert seen[0].blocks(IN_THE_DOORWAY)
    monkeypatch.setattr(module, 'PASSED_OPEN', True)
    assert passed.seen(HALLS, [SHUT], [NORTH]) == (SHUT,)  # nothing was remembered while off


# The shot through a closed door of 2026-10-24 (doors.py SHOT_LEAF, rca/2026-10-24/closed-door-findings.md): take
# 20261024T173021Z-69, Tal Rasha's Tomb. The TombDoorLeft 2303763190 (1 x 7 at (22680, 9862)) read 0 from 20:32:20 until
# the player opened it at 20:32:33.9; the tier 5 Herald 3633126376 stood pressed into its doorway from the west at
# (22680.5, 9863.5), its bound demon beside it. From the west the blades hit it (20:32:25-27); from the east every
# volley turned at x 22680.8-22681.6, the door's face (20:32:30-33), and the Herald lost life only to the demon.
TOMB_DOOR_LEFT = 91  # objects.txt, 1 x 7
HERALD_DOOR = Door(2303763190, TOMB_DOOR_LEFT, module.CLOSED_MODE, 22680.0, 9862.0)
HERALD = (22680.5, 9863.5)
EAST = (22684.5, 9874.5)  # the character at 20:32:27.6-33.4, striking through the door
WEST = (22661.5, 9858.5)  # the character at 20:32:24-27, striking the Herald on its own side
EARLIER = ((22687.5, 9873.5), (22680.5, 9863.5))  # 20:31:42.6-47: the character, the monster 4124608155 struck
BESIDE = ((22684.5, 9872.5), (22682.5, 9867.5))  # 20:31:37-40: the monster 2841478249 east of the door, the same side


@pytest.fixture
def leaf(monkeypatch):
    monkeypatch.setattr(module, 'SHOT_LEAF', True)


def test_a_monster_pressed_into_a_closed_doorway_is_behind_the_door_from_its_far_side(leaf) -> None:
    assert HERALD_DOOR.crosses(EAST, HERALD)
    assert not clear_shot(Ground(()), EAST, HERALD, (HERALD_DOOR,))
    assert not clear_shot(Ground(()), *EARLIER, (HERALD_DOOR,))


def test_from_its_own_side_the_monster_in_the_doorway_is_struck(leaf) -> None:
    assert not HERALD_DOOR.crosses(WEST, HERALD)
    assert clear_shot(Ground(()), WEST, HERALD, (HERALD_DOOR,))
    assert clear_shot(Ground(()), *BESIDE, (HERALD_DOOR,))


def test_the_switch_off_reads_the_far_side_shot_clear_as_before(monkeypatch) -> None:
    monkeypatch.setattr(module, 'SHOT_LEAF', False)
    assert clear_shot(Ground(()), EAST, HERALD, (HERALD_DOOR,))  # the box looked at between the margins only
    assert clear_shot(Ground(()), WEST, HERALD, (HERALD_DOOR,))


@pytest.mark.parametrize('mode', [1, 2])
def test_an_opening_or_opened_door_has_no_leaf_in_the_way(leaf, mode) -> None:
    opened = Door(HERALD_DOOR.unit_id, TOMB_DOOR_LEFT, mode, HERALD_DOOR.x, HERALD_DOOR.y)
    assert not opened.crosses(EAST, HERALD)
    assert clear_shot(Ground(()), EAST, HERALD, (opened,))  # struck through it from 20:32:34 on: it died at 35.3


def test_a_passed_door_has_no_leaf_in_the_way(leaf) -> None:
    assert not replace(HERALD_DOOR, passed=True).crosses(EAST, HERALD)


@pytest.mark.parametrize(
    ('near', 'far'),
    [
        ((22721.5, 9609.1), (22721.5, 9611.5)),  # pressed on both sides: -0.9 and +1.5 off the anchor, 2.4 apart
        ((22721.5, 9605.0), (22721.5, 9611.5)),
        ((22721.5, 9609.5), (22722.0, 9630.0)),
    ],
)
def test_a_line_across_the_leaf_is_blocked_however_short_and_whichever_way(leaf, near, far) -> None:
    door = Door(2121110066, TOMB_DOOR_RIGHT, module.CLOSED_MODE, 22721.0, 9610.0)  # the 7 x 1 door of the take
    assert door.crosses(near, far)
    assert door.crosses(far, near)
    assert not clear_shot(Ground(()), near, far, (door,))


def test_a_line_past_the_door_s_end_and_frame_is_not_blocked_by_it(leaf) -> None:
    door = Door(2121110066, TOMB_DOOR_RIGHT, module.CLOSED_MODE, 22721.0, 9610.0)  # its box 22716.5-22725.5 along
    assert door.crosses((22716.7, 9605.0), (22716.7, 9615.0))  # in the frame
    assert not door.crosses((22716.3, 9605.0), (22716.3, 9615.0))  # past the frame's end
    assert not door.crosses((22725.7, 9605.0), (22725.7, 9615.0))
    assert not door.crosses((22715.0, 9609.5), (22730.0, 9609.5))  # along it, on one side
