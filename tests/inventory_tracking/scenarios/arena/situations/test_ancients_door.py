"""The Icy Cellar's door with the staff empty on the take's ground
(ancients_door.py; rca/2026-10-14/run-1932-findings.md
§1.2.2, rca/2026-10-14/navigation-classes.md). On 2026-10-14 at 22:54:28-40 the presses of the teleport key walked
into the pocket D, 43 units from the door in a straight line and 276 by the walked way, and stopped there on "no Blade
Warp or walk leads toward Icy Cellar" three times. Played on that ground before the navigation classes, the key held
from D moved nothing (149 such stops in 25 s) and from B walked into D. Each press now goes by the class in hand (the
walked way, a Blade Warp over a clear line where it beats the walk), by the pursuit loop (the pursuit-off variant
was deleted 2026-10-19)."""

import functools
import math
from itertools import pairwise

import pytest

from tests.inventory_tracking.scenarios.arena.situations import ancients_door
from tests.inventory_tracking.scenarios.arena.situations.ancients_door import AT_DOOR, DOOR, POCKET, B, D, standing
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, dump, held, load
from tests.inventory_tracking.scenarios.arena.situations.test_pursuit_situations import Watch, watched


SEEDS = (1, 2, 3)
SECONDS = 25.0  # the player walked it by hand in 16 s; the Blade Warps take 15 to 17
STOP = 'leads toward Icy Cellar'


@functools.cache
def pressed(start: str, logic: str, seed: int) -> Watch:
    """The teleport key held every 0.3 s from `start` ('D' or 'B'), the staff empty, watched with the navigator's eta
    to the door at every tick."""
    base = standing(ancients_door.stored(), {'D': D, 'B': B}[start])
    return watched(base.logic(logic), [held('teleport', every=0.3)], seed, DOOR, SECONDS)


def test_the_fixture_loads_without_its_take_and_writes_back_the_same(tmp_path) -> None:
    path = FIXTURES / f'{ancients_door.NAME}.json'
    situation = load(path)
    dump(situation, tmp_path / 'again.json')
    assert (tmp_path / 'again.json').read_text(encoding='utf-8') == path.read_text(encoding='utf-8')


def test_the_moment_is_the_takes() -> None:
    base = ancients_door.stored()
    assert base.source is not None
    assert base.source['take'] == ancients_door.TAKE
    assert base.scene.hero.sets[1].teleport_charges == 0
    assert math.dist(base.scene.hero.at, ancients_door.A) < 1.0
    assert base.attack
    assert len(base.presses) == 24
    assert {routine for _, routine in base.presses} == {'teleport'}
    assert any(mark.label == 'Icy Cellar' for mark in base.marks)


@pytest.mark.xdist_group('ancients: the door')
@pytest.mark.parametrize('start', ['D', 'B'])
def test_the_held_key_comes_to_the_door_along_the_walked_way(start: str) -> None:
    for seed in SEEDS:
        watch = pressed(start, 'new', seed)
        outcome = watch.outcome
        assert not outcome.dead, seed
        assert not [text for _, text in outcome.said if STOP in text], seed
        assert ancients_door.first_at_door(outcome.track) is not None, seed
        assert min(math.dist(here, DOOR) for _, here, _, _, _ in watch.rows) <= AT_DOOR
        assert math.dist(watch.rows[-1][1], D) > POCKET, seed  # out of the pocket at the end


@pytest.mark.xdist_group('ancients: the door')
@pytest.mark.parametrize('start', ['D', 'B'])
def test_the_way_left_to_the_door_never_grows_between_two_presses(start: str) -> None:
    """Progress by the navigator's own measure (`MovementSet.eta`, the walked way at the class's pace): from one press
    to the next it never rises, from 276 units by the walked way in the pocket."""
    for seed in SEEDS:
        watch = pressed(start, 'new', seed)
        reached = ancients_door.first_at_door(watch.outcome.track)
        assert reached is not None
        etas = [watch.eta_at(at) for at in watch.presses if at < reached]
        assert etas[0] > 5.0, seed
        assert all(later <= earlier + 1e-9 for earlier, later in pairwise(etas)), (seed, etas)
