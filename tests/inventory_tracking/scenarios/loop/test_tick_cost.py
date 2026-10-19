"""What a decision tick costs, on a recorded Catacombs frame: regression bounds on the work done (cell
asks and door tests, which do not depend on the host), a loose wall-time sanity bound beside them, and the
wall-time bounds wanted (marked `slow`: nice 19 on a busy host makes wall time noisy). tick_cost.py prints
the same numbers in milliseconds for any take.
"""

import math
import time
from collections import Counter
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.echoing_strike.attack import REACH
from inventory_tracking.game.records import Player
from inventory_tracking.game.view import Viewport
from inventory_tracking.levels.doors import CLOSED_MODE, Door
from inventory_tracking.levels.model import Ground, Target
from inventory_tracking.macros.hunt import DECIDE_SECONDS, SIGHT, Hunter, hostiles
from inventory_tracking.macros.sight import in_reach
from inventory_tracking.macros.teleport import Way, landing
from tests.inventory_tracking.macros.fakes import warlock
from tests.inventory_tracking.scenarios.loop.helpers import ASPECT, TICK, busiest_frame, recorded, recorded_world
from tests.inventory_tracking.scenarios.loop.tick_cost import decision, fastest


@pytest.fixture(scope='module')
def scene():
    take, ground, rooms, grids = recorded()
    return busiest_frame(take), ground, rooms, grids


def counted(monkeypatch) -> Counter:
    """Calls of the two things a decision spends its time in: grid cells asked (Ground.walkable) and door
    tests (Door.blocks). They do not depend on the host, and sit at the boundary the geometry is asked through."""
    calls: Counter = Counter()
    for cls, name in ((Ground, 'walkable'), (Door, 'blocks')):
        original = getattr(cls, name)

        def wrapped(self, *args, _name=name, _original=original):
            calls[_name] += 1
            return _original(self, *args)

        monkeypatch.setattr(cls, name, wrapped)
    return calls


# Counted 2026-10-19 on the recorded Catacombs frame (deterministic): walkable 5.5k, 19.2k, 50.3k and blocks 11.1k,
# 38.3k, 100.5k for 5, 20, 60 hostiles; the bounds are 1.5x. The wall limits are 10x today's worst, a sanity check only.
@pytest.mark.parametrize(
    ('count', 'cells', 'doors', 'limit'),
    [(5, 8_500, 17_000, 5.0), (20, 29_000, 58_000, 15.0), (60, 76_000, 151_000, 50.0)],
)
def test_a_decision_stays_within_the_work_it_does_today(scene, monkeypatch, count, cells, doors, limit):
    frame, ground, _, _ = scene
    seen = recorded_world(frame, count)
    hunter = Hunter(build=warlock(seen))
    assert seen.player is not None
    here = (seen.player.x, seen.player.y)
    foes = hostiles(seen)
    reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), REACH, seen.doors)]
    near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT]
    calls = counted(monkeypatch)
    began = time.perf_counter()
    hunter.choose(seen, foes, reachable or near[:1], ground, Viewport(ASPECT))
    assert time.perf_counter() - began < limit
    assert calls['walkable'] <= cells
    assert calls['blocks'] <= doors


@pytest.mark.slow  # wall time: host-dependent
@pytest.mark.xfail(
    strict=True,
    reason='LinePolicy.choose lays three lines through every hostile in reach and flies five blades along each '
    'against every hostile and every closed door of the level: 96 to 600 ms for 60 hostiles on recorded Catacombs '
    'grounds, 18 to 112 ms for 20. In the fights recorded so far (6 hostiles in sight at the median, 36 at most) '
    'it is 10 ms at the median, 33 at p90, 118 at worst; meanwhile the left button goes unlooked at',
)
def test_a_decision_over_sixty_hostiles_fits_between_two_looks_of_the_fight(scene):
    # The fight asks again every DECIDE_SECONDS and looks at the player's button every tick: a
    # decision longer than a tick is a tick the button, the casts and a cancel go unseen. (Twenty
    # hostiles cost 72 to 112 ms here: over the tick too, but too near it to mark on a busy host.)
    frame, ground, _, _ = scene
    cost = decision(recorded_world(frame, 60), ground)
    assert cost['choose'] / 1000 <= TICK
    assert TICK < DECIDE_SECONDS


def test_the_reach_of_sixty_hostiles_is_told_in_few_cell_asks(scene, monkeypatch):
    # Twice a look in a fight and once while idle. Counted 2026-10-19: 850 cells, 1.65k door tests; bounds 1.5x.
    frame, ground, _, _ = scene
    seen = recorded_world(frame, 60)
    assert seen.player is not None
    here = (seen.player.x, seen.player.y)
    foes = hostiles(seen)
    calls = counted(monkeypatch)
    [in_reach(ground, here, (m.x, m.y), REACH, seen.doors) for m in foes]
    assert calls['walkable'] <= 1_300
    assert calls['blocks'] <= 2_500


@pytest.mark.xfail(
    strict=True,
    reason='policy.walls asks every closed door of the level about every point a blade passes, however far the '
    'door is: 45% of a decision on a recorded Catacombs frame with 15 closed doors (cProfile, 441,630 calls of '
    'Door.blocks in three decisions over 60 hostiles)',
)
def test_doors_out_of_the_blades_reach_are_not_asked_about_every_blade(scene, monkeypatch):
    frame, ground, _, _ = scene
    seen = recorded_world(frame, 20)
    assert seen.player is not None
    here = (seen.player.x, seen.player.y)
    far = tuple(
        Door(900 + index, door.txt_id, CLOSED_MODE, here[0] + 80.0 + 10 * index, here[1] + 80.0)
        for index, door in enumerate(seen.doors)
    )
    assert far  # the frame has doors
    seen = replace(seen, doors=far)
    asked = []
    blocks = Door.blocks

    def counted(self, point):
        asked.append(self.unit_id)
        return blocks(self, point)

    monkeypatch.setattr(Door, 'blocks', counted)
    foes = hostiles(seen)
    reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), REACH, seen.doors)]
    asked.clear()  # the reach asks them too, once a sample: the decision is what is counted
    Hunter(build=warlock(seen)).choose(seen, foes, reachable, ground, Viewport(ASPECT))
    assert asked == []


def plan(scene):
    frame, _, rooms, grids = scene
    row = frame['p']
    stand = Player(row[0], 'CybergrindAA', 1, row[2], row[3], row[4], False)
    target = Target(row[2], rooms, (rooms[0].x + 0.5, rooms[0].y + 0.5), 'the elite', 'hunt', False, grids)
    return target, stand, Way(target, Viewport(ASPECT))


def test_a_hops_landing_is_found_within_the_work_it_does_today(scene, monkeypatch):
    # Counted 2026-10-19: 6.1k cell asks on this 12-room level; bound 1.5x. Wall: 10x today's worst (131 ms).
    target, stand, way = plan(scene)
    calls = counted(monkeypatch)
    assert fastest(lambda: landing(target, stand, way, ASPECT), 1) / 1000 < 1.3
    assert calls['walkable'] <= 9_200


@pytest.mark.slow  # wall time: host-dependent
def test_a_hops_landing_is_found_within_a_quarter_tick(scene):
    target, stand, way = plan(scene)
    assert fastest(lambda: landing(target, stand, way, ASPECT), 3) / 1000 <= TICK / 4
