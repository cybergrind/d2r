"""macros/hopway.py: the lazy hop potential answers as teleport.py's `Way` does, on recorded levels."""

import json
import math
import random
from functools import cache
from pathlib import Path

import pytest

from inventory_tracking.levels.model import Room, Target, Walkable
from inventory_tracking.macros import hopway, teleport
from inventory_tracking.macros.movement import Stand
from inventory_tracking.native.layout import TILE_UNITS


FIXTURES = Path(__file__).parents[1] / 'scenarios' / 'exits' / 'fixtures'
LEVELS = ('catacombs2_stairs291', 'catacombs3_stairs292_doors', 'catacombs4')
DURIELS_LAIR = 73  # the one level whose Teleport needs a clear line (levels/reach.py `lined`)


@cache
def level(name: str) -> tuple[int, tuple[Room, ...], tuple[Walkable, ...], tuple[float, float]]:
    found = json.loads((FIXTURES / f'{name}.json').read_text())
    rooms = tuple(
        Room(
            row['preset'], row['x'], row['y'], row['width'], row['height'], row.get('variant'),
            tuple(row['block']) if row.get('block') else None, tuple(row.get('leads_to') or ()),
        )
        for row in found['rooms']
    )  # fmt: skip
    grids = tuple(Walkable(**grid) for grid in found['ground'])
    return found['area'], rooms, grids, tuple(found['arrived_at'])


def tiles(rooms: tuple[Room, ...], rng: random.Random, count: int) -> list[tuple[float, float]]:
    """Random points (tiles) on the rooms."""
    out = []
    for _ in range(count):
        room = rng.choice(rooms)
        out.append((room.x + rng.uniform(0, room.width), room.y + rng.uniform(0, room.height)))
    return out


def targets(name: str, area: int | None = None, warp: bool = False, count: int = 6) -> list[Target]:
    found_area, rooms, grids, _ = level(name)
    rng = random.Random(name)
    return [
        Target(found_area if area is None else area, rooms, point, 'the goal', 'hunt', warp, grids)
        for point in tiles(rooms, rng, count)
    ]


@pytest.fixture(params=[False, True], ids=['dijkstra', 'astar'], autouse=True)
def astar(request, monkeypatch) -> bool:
    """Every test with the potential grown both ways (hopway.py ASTAR_HOPS, 2026-10-24): the same answers."""
    monkeypatch.setattr(hopway, 'ASTAR_HOPS', request.param)
    return request.param


@pytest.mark.parametrize('name', LEVELS)
@pytest.mark.parametrize('far', [True, False])
@pytest.mark.parametrize('area', [None, DURIELS_LAIR])
def test_every_way_is_the_full_potentials(name: str, far: bool, area: int | None) -> None:
    rooms = level(name)[1]
    rng = random.Random(f'{name}{far}{area}')
    for target in targets(name, area, count=3):
        full, lazy = teleport.Way(target, far=far), hopway.LazyWay(target, far=far)
        for point in tiles(rooms, rng, 60):
            assert lazy.from_here(point) == full.from_here(point)
            assert lazy.to_go(point) == full.to_go(point)
        lazy.to_go_below(target.point, math.inf)  # grown out: every tile the full potential costs
        assert {tile: lazy.cost[tile] for tile in lazy.settled} == full.cost


@pytest.mark.parametrize('name', LEVELS)
@pytest.mark.parametrize('far', [True, False])
@pytest.mark.parametrize('area', [None, DURIELS_LAIR])
@pytest.mark.parametrize('warp', [False, True])
@pytest.mark.parametrize('ring', [None, (12.0, 26.0)])
def test_the_landing_is_the_full_potentials_and_grows_less(
    name: str, far: bool, area: int | None, warp: bool, ring: tuple[float, float] | None
) -> None:
    rooms, grids = level(name)[1:3]
    rng = random.Random(f'{name}{far}{area}{warp}{ring}')
    grown = []
    for target in targets(name, area, warp, count=4):
        full = teleport.Way(target, far=far)
        for start in tiles(rooms, rng, 8):
            lazy = hopway.LazyWay(target, far=far)  # fresh: as a new goal's
            player = Stand(start[0] * TILE_UNITS, start[1] * TILE_UNITS)
            aspect = teleport.HOST_VIEW.aspect
            # A place for the player, as movement.py `hop_leg` passes it: `landing` reads only x and y
            wanted = teleport.landing(target, player, full, aspect, ring)  # pyrefly: ignore[bad-argument-type]
            assert hopway.landing(target, player, lazy, aspect, ring) == wanted
            if full.cost:
                grown.append(len(lazy.settled) / len(full.cost))
    assert grids
    assert sum(grown) / len(grown) < 1.0  # some landings settle part of the level only


def test_a_kept_way_grows_on_from_where_it_stopped() -> None:
    target = targets('catacombs4', count=1)[0]
    rooms = level('catacombs4')[1]
    full, lazy = teleport.Way(target), hopway.way_for(target)
    near = (target.point[0] + 1.2, target.point[1] + 0.7)
    lazy.from_here(near)
    first = len(lazy.settled)
    far = max(tiles(rooms, random.Random(1), 200), key=lambda point: math.dist(point, target.point))
    assert lazy.from_here(far) == full.from_here(far)
    assert len(lazy.settled) >= first
    assert hopway.way_for(target) is lazy  # the same target: the same potential, kept


def test_the_landable_tiles_are_kept_per_level() -> None:
    _, rooms, grids, _ = level('catacombs2_stairs291')
    assert hopway.landable_tiles(rooms, grids) is hopway.landable_tiles(rooms, grids)
    one, other = targets('catacombs2_stairs291', count=2)
    for target in (one, other):
        mark = (math.floor(target.point[0]), math.floor(target.point[1]))
        assert hopway.LazyWay(target).landable == hopway.landable_tiles(rooms, grids) | {mark}


@pytest.mark.parametrize('name', LEVELS)
def test_below_a_bound_every_way_is_known_and_none_above(name: str) -> None:
    rooms = level(name)[1]
    rng = random.Random(name)
    for target in targets(name, count=3):
        full = teleport.Way(target)
        for bound in (0.5, 2.0, 4.5, 9.0):
            lazy = hopway.LazyWay(target)
            for point in tiles(rooms, rng, 80):
                cost = full.cost.get((math.floor(point[0]), math.floor(point[1])))
                wanted = full.to_go(point) if cost is not None and cost <= bound else math.inf
                assert lazy.to_go_below(point, bound) == wanted


# movement.py LAZY_HOPS (2026-10-23): the hop leg by the lazy potential is the leg by the full one


@pytest.mark.parametrize('name', LEVELS)
@pytest.mark.parametrize('charges', [30, 2])
@pytest.mark.parametrize('intent', ['PRESSED', 'SAFE_MOVE', 'STANDING'])
def test_the_hop_leg_is_the_same_with_the_lazy_potential(monkeypatch, name: str, charges: int, intent: str) -> None:
    from inventory_tracking.game.records import Teleport
    from inventory_tracking.levels.model import Ground
    from inventory_tracking.macros import movement, travel
    from inventory_tracking.macros.build import MoveFacts
    from inventory_tracking.macros.skills import TELEPORT

    area, rooms, grids, _ = level(name)
    rng = random.Random(f'leg{name}{charges}')
    ground = Ground(grids)
    legs = {False: [], True: []}
    starts = [(x * TILE_UNITS, y * TILE_UNITS) for x, y in tiles(rooms, rng, 8)]
    goals = [(x * TILE_UNITS, y * TILE_UNITS) for x, y in tiles(rooms, rng, 8)]
    for lazy in (False, True):
        monkeypatch.setattr(movement, 'LAZY_HOPS', lazy)
        for here, goal in zip(starts, goals, strict=True):
            facts = MoveFacts(here, 100.0, (TELEPORT,), Teleport(charges, 69, True), ground, (), 16 / 9, area=area,
                              rooms=rooms)  # fmt: skip
            legs[lazy].append((movement.hop_leg(facts, goal, getattr(travel, intent)), movement.hops_left(facts, goal)))
    assert legs[True] == legs[False]
    assert any(not isinstance(leg, movement.NoWay) for leg, _ in legs[True])


@pytest.mark.parametrize('name', LEVELS)
def test_grown_toward_the_character_a_far_goal_settles_fewer_tiles(monkeypatch, name: str, astar: bool) -> None:
    # 2026-10-24 (rca/2026-10-24/realtime-4-findings.md §2): live, a new far goal's potential settled ~4000 tiles
    if not astar:
        pytest.skip('the A* growth only')
    rooms = level(name)[1]
    rng = random.Random(f'grow{name}')
    settled: dict[bool, int] = {False: 0, True: 0}
    for target in targets(name, count=4):
        starts = sorted(tiles(rooms, rng, 40), key=lambda point: math.dist(point, target.point))[-4:]  # the far ones
        for start in starts:
            player = Stand(start[0] * TILE_UNITS, start[1] * TILE_UNITS)
            found = {}
            for on in (False, True):
                monkeypatch.setattr(hopway, 'ASTAR_HOPS', on)
                lazy = hopway.LazyWay(target, far=True)
                found[on] = hopway.landing(target, player, lazy, teleport.HOST_VIEW.aspect)
                settled[on] += len(lazy.settled)
            assert found[True] == found[False]
    assert settled[True] < settled[False]
