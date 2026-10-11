"""What a decision tick costs in wall time, on a recorded Catacombs frame: bounds that catch a
regression, and the bounds wanted.

Wall time is noisy (other work on the host only ever adds), so each call is timed several times and
the fastest kept, a regression bound is several times today's cost, and a wanted bound is marked as
failing only where today's cost is several times over it. Counts stand in for time where they can:
they do not depend on the host. tick_cost.py prints the same numbers for any take.
"""

from dataclasses import replace

import pytest

from inventory_tracking.combat.policy import REACH
from inventory_tracking.levels.doors import CLOSED_MODE, Door
from inventory_tracking.levels.model import Target
from inventory_tracking.macros.hunt import DECIDE_SECONDS, Hunter, hostiles
from inventory_tracking.macros.sight import in_reach
from inventory_tracking.macros.teleport import Way, landing
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import Player
from tests.inventory_tracking.scenarios.loop.helpers import ASPECT, TICK, busiest_frame, recorded, recorded_world
from tests.inventory_tracking.scenarios.loop.tick_cost import decision, fastest


@pytest.fixture(scope='module')
def scene():
    take, ground, rooms, grids = recorded()
    return busiest_frame(take), ground, rooms, grids


@pytest.mark.parametrize(('count', 'limit'), [(5, 0.5), (20, 1.5), (60, 5.0)])
def test_a_decision_stays_within_many_times_what_it_costs_today(scene, count, limit):
    # Today, the fastest of 5 on the host with other work running: 15 to 23 ms, 72 to 112 ms, 350 to 600 ms.
    frame, ground, _, _ = scene
    cost = decision(recorded_world(frame, count), ground)
    assert cost['choose'] / 1000 < limit


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


def test_the_reach_of_sixty_hostiles_is_told_well_within_a_tick(scene):
    # Twice a look in a fight and once while idle: 2 to 4 ms today.
    frame, ground, _, _ = scene
    seen = recorded_world(frame, 60)
    here = (seen.player.x, seen.player.y)
    foes = hostiles(seen)
    cost = fastest(lambda: [in_reach(ground, here, (m.x, m.y), REACH, seen.doors) for m in foes])
    assert cost / 1000 < TICK / 2


@pytest.mark.xfail(
    strict=True,
    reason='policy.walls asks every closed door of the level about every point a blade passes, however far the '
    'door is: 45% of a decision on a recorded Catacombs frame with 15 closed doors (cProfile, 441,630 calls of '
    'Door.blocks in three decisions over 60 hostiles)',
)
def test_doors_out_of_the_blades_reach_are_not_asked_about_every_blade(scene, monkeypatch):
    frame, ground, _, _ = scene
    seen = recorded_world(frame, 20)
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
    Hunter().choose(seen, foes, reachable, ground, Viewport(ASPECT))
    assert asked == []


def plan(scene):
    frame, _, rooms, grids = scene
    row = frame['p']
    stand = Player(row[0], 'CybergrindAA', 1, row[2], row[3], row[4], False)
    target = Target(row[2], rooms, (rooms[0].x + 0.5, rooms[0].y + 0.5), 'the elite', 'hunt', False, grids)
    return target, stand, Way(target, Viewport(ASPECT))


def test_a_hops_landing_is_found_within_many_times_what_it_costs_today(scene):
    # Today 47 to 50 ms on this 12-room level, 113 to 131 ms on a 15-room one.
    target, stand, way = plan(scene)
    assert fastest(lambda: landing(target, stand, way, ASPECT), 3) / 1000 < 1.0


def test_a_hops_landing_is_found_within_a_quarter_tick(scene):
    target, stand, way = plan(scene)
    assert fastest(lambda: landing(target, stand, way, ASPECT), 3) / 1000 <= TICK / 4
