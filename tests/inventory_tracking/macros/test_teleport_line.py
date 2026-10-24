"""One reachability fact for a Teleport (levels/reach.py `hop_lands`), as the hop planner (teleport.py `Way`,
`landing`), the stride (travel.py `jump_lands`) and the explore target (hunt.py `frontier`) use it; and the spot the
safety drops binding the pursuit's act of the same look (hunting/moves.py DUD_BINDS).

The case: Duriel's Lair, 15:15:06.8-15:15:26 on 2026-10-23 (take 20261023T121459Z-73; rca/2026-10-23/gap-findings.md):
"agenda: target an unexplored room", then Teleports to (22603.3, 15703.1) across the lair's wall, each one cast and
nothing moved, 19 s until the run passed the room."""

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from inventory_tracking.levels import reach
from inventory_tracking.levels.model import Ground, Level, Room, Walkable, pack_cells, pack_masks
from inventory_tracking.macros import movement, teleport
from inventory_tracking.macros.build import MoveFacts
from inventory_tracking.macros.goals import FIGHT, Goal
from inventory_tracking.macros.hunting import moves
from inventory_tracking.macros.pursuit import Move
from inventory_tracking.macros.safety import DUD_UNITS
from inventory_tracking.macros.skills import TELEPORT
from inventory_tracking.macros.travel import PRESSED, Step
from tests.inventory_tracking.macros.test_hunt import game, hunter, keys, me


FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'duriels_lair_gap.json'
LAIR, CANYON = 73, 46  # levels.txt Teleport 2 and 1
HERE = (22622.5, 15692.5)
ROOM = (22577.5, 15697.5)  # the unexplored room's tile centre the agenda targeted (room 481 at (4515, 3139))
ACROSS = (22603.3, 15703.1)  # the hop the game refused
ASPECT = 2560 / 1418
RECT = (1920, 0, 2560, 1418)


@pytest.fixture
def line(monkeypatch):
    """Sets TELEPORT_LINE; the hop potentials kept by `way_for` are dropped before and after."""

    def switch(on: bool) -> None:
        monkeypatch.setattr(reach, 'TELEPORT_LINE', on)
        teleport.way_for.cache_clear()
        teleport.FAR_FAILED.clear()

    yield switch
    teleport.way_for.cache_clear()
    teleport.FAR_FAILED.clear()


def lair() -> tuple[tuple[Room, ...], Ground]:
    level = json.loads(FIXTURE.read_text())
    rooms = tuple(
        Room(
            row['preset'], row['x'], row['y'], row['width'], row['height'], row['variant'],
            tuple(row['block']) if row['block'] else None, tuple(row['leads_to']),
        )
        for row in level['rooms']
    )  # fmt: skip
    return rooms, Ground(tuple(Walkable(**grid) for grid in level['ground']))


def facts(here, ground: Ground, rooms: tuple[Room, ...], area: int) -> MoveFacts:
    """The character's own Teleport (no staff), as in the take."""
    return MoveFacts(
        here=here, now=100.0, slots=(TELEPORT,), staff=None, ground=ground, doors=(), aspect=ASPECT, area=area,
        rooms=rooms,
    )  # fmt: skip


def hops(here, ground, rooms, area, goal, most=10) -> list[Step]:
    """The hop legs `hop_leg` plans one after the other from `here` until it arrives (or `most` of them)."""
    made = []
    for _ in range(most):
        leg = movement.hop_leg(facts(here, ground, rooms, area), goal, PRESSED)
        if not isinstance(leg, Step):
            break
        made.append(leg)
        here = leg.spot
    return made


@pytest.mark.parametrize('on', [True, False])
def test_the_lairs_hop_across_its_wall_is_not_planned_with_the_switch_on(line, on):
    line(on)
    rooms, ground = lair()
    made = hops(HERE, ground, rooms, LAIR, ROOM)
    assert made
    assert all(step.skill == TELEPORT for step in made)
    assert math.dist(made[-1].spot, ROOM) < 1.0  # the room is reached either way
    if not on:
        # As today: straight at the wall, a hop the game refuses
        assert made[0].spot == pytest.approx(ACROSS, abs=0.1)
        assert not reach.line_clear(ground, HERE, made[0].spot)
        return
    # Round the wall's end by hops the game makes, never at the refused spot
    starts = (HERE, *(step.spot for step in made[:-1]))
    assert all(reach.line_clear(ground, start, step.spot) for start, step in zip(starts, made, strict=True))
    assert all(math.dist(step.spot, ACROSS) > DUD_UNITS for step in made)
    assert len(made) <= 6


def test_elsewhere_a_hop_crosses_the_same_wall(line):
    line(True)
    rooms, ground = lair()
    made = hops(HERE, ground, rooms, CANYON, ROOM)
    assert made[0].spot == pytest.approx(ACROSS, abs=0.1)


def corridor(mask: int) -> Ground:
    """Floor 5 tiles by 1, a column of 3 sub-tiles at x 10-12 nobody walks on, with raw `mask`."""
    width = 25
    cells = ''.join('0' if 10 <= x <= 12 else '1' for _ in range(5) for x in range(width))
    masks = [mask if 10 <= x <= 12 else 0 for _ in range(5) for x in range(width)]
    return Ground((Walkable(0, 0, 5, 1, pack_cells(cells), '', pack_masks(masks)),))


@pytest.mark.parametrize('on', [True, False])
def test_a_hop_over_a_small_gap_still_plans_and_one_over_a_barrier_does_not(line, on):
    line(on)
    here, goal = (2.5, 2.5), (20.5, 2.5)
    # A gap of 3 the character cannot walk but a missile flies over (mask 0x0001): the stride hops it
    over = movement.hop_leg(facts(here, corridor(0x0001), (), LAIR), goal, PRESSED)
    assert isinstance(over, Step)
    assert over.skill == TELEPORT
    assert over.spot[0] > 12
    # The same gap barring a flying player (0x0004): in the lair no hop over it with the switch on
    barred = movement.hop_leg(facts(here, corridor(0x0005), (), LAIR), goal, PRESSED)
    if on:
        assert not (isinstance(barred, Step) and barred.skill == TELEPORT)
    else:
        assert isinstance(barred, Step)
        assert barred.skill == TELEPORT
    elsewhere = movement.hop_leg(facts(here, corridor(0x0005), (), CANYON), goal, PRESSED)
    assert isinstance(elsewhere, Step)
    assert elsewhere.skill == TELEPORT


def walled_rooms(gap: int) -> tuple[tuple[Room, ...], tuple[Walkable, ...]]:
    """Room A (where the character stands) and room B east of it, 8x8 tiles each, B's first `gap` sub-tile columns
    a wall barring walk and flight (mask 0x0805): nothing walks from A to B."""
    a, b = Room(500, 1000, 1000, 8, 8), Room(501, 1008, 1000, 8, 8)
    floor = Walkable(a.x, a.y, 8, 8, pack_cells('1' * 1600), '', pack_masks([0] * 1600))
    rows = [(x, y) for y in range(40) for x in range(40)]
    cells = ''.join('0' if x < gap else '1' for x, _ in rows)
    masks = [0x0805 if x < gap else 0 for x, _ in rows]
    return (a, b), (floor, Walkable(b.x, b.y, 8, 8, pack_cells(cells), '', pack_masks(masks)))


@pytest.mark.parametrize(('on', 'area', 'gap', 'target'), [
    (True, LAIR, 10, False),  # behind the lair's wall: no hop the game makes and no walk gets there
    (False, LAIR, 10, True),  # as today: the potential crosses the wall
    (True, CANYON, 10, True),  # elsewhere a Teleport crosses it
    (True, CANYON, 39, False),  # elsewhere too, past every hop in view: no target (as before)
])  # fmt: skip
def test_an_unexplored_room_no_walk_or_teleport_reaches_is_no_target(line, on, area, gap, target):
    line(on)
    rooms, grids = walled_rooms(gap)
    play = game()
    hunt = hunter(play)
    level = Level(area, rooms, grids)
    player = replace(me(play.world), x=(1004 * 5) + 2.5, y=(1004 * 5) + 2.5, area=area)
    found = hunt.frontier(level, player, RECT)
    assert (found is not None and found[1] == rooms[1]) is target


@pytest.mark.parametrize('on', [True, False])
def test_dropped(monkeypatch, on):
    monkeypatch.setattr(moves, 'DUD_BINDS', on)
    goal = Goal('full clear: an unexplored room', ROOM, FIGHT, 5.0, PRESSED)
    hop, walk = Move(Step(ACROSS, TELEPORT), goal), Move(Step(ACROSS), goal)
    duds = {ACROSS: 30.0}
    assert moves.dropped(hop, duds, DUD_UNITS, 10.0) is on
    assert not moves.dropped(hop, duds, DUD_UNITS, 31.0)  # its 20 s over
    assert not moves.dropped(walk, duds, DUD_UNITS, 10.0)  # a walk there may well get there
    far = Move(Step((ACROSS[0] + 4.0, ACROSS[1]), TELEPORT), goal)
    assert not moves.dropped(far, duds, DUD_UNITS, 10.0)


@pytest.mark.parametrize('on', [True, False])
def test_a_spot_the_safety_drops_in_the_look_is_not_pressed_by_that_looks_act(monkeypatch, on):
    # 15:15:10.49 "the spot is dropped for 20s", 15:15:10.52 the same look's act pressed it again
    from inventory_tracking.macros.hunting.base import Judged

    monkeypatch.setattr(moves, 'DUD_BINDS', on)
    play = game()
    hunt = hunter(play)
    run = play.run()
    here = me(play.world)
    spot = (here.x - 19.0, here.y + 10.0)
    goal = Goal('full clear: an unexplored room', (here.x - 45.0, here.y + 5.0), FIGHT, 5.0, PRESSED)
    hop = Move(Step(spot, TELEPORT), goal)
    monkeypatch.setattr(hunt, 'judge', lambda *args, **kwargs: Judged(hop, goal, goal.place, None))
    made: list[Move] = []
    monkeypatch.setattr(hunt, 'advance', lambda run, world, ground, act, *rest: made.append(act))
    hunt.safety.duds = {spot: run.clock() + 20.0}
    assert hunt.pursue(run, play.world, [], Ground(()), keys, in_reach=False)
    assert made == ([] if on else [hop])
