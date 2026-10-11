"""What one decision tick costs, on recorded play and without the game: milliseconds per call.

The scene is a frame of a take (the checked-in Catacombs trim by default, or a take directory given
on the command line): the character, the monsters where they stood, the doors, the level's grids.
Packs larger than the frame's are the same monsters again on rings around the character (synthetic:
the Catacombs takes never held more than 36 hostiles in sight). Each call is timed `ROUNDS` times and
the fastest is kept: other work on the host only ever adds.

    uv run --offline python -m tests.inventory_tracking.scenarios.loop.tick_cost [take directory]
"""

import gzip
import json
import math
import sys
import time
from collections.abc import Callable
from pathlib import Path

from inventory_tracking.combat.policy import REACH, STRIKE_REACH, observe
from inventory_tracking.combat.takes import Take
from inventory_tracking.levels.model import Ground, Room, Target, Walkable
from inventory_tracking.macros.hunt import SIGHT, Hunter, hostiles
from inventory_tracking.macros.sight import clear_shot, firing_spots, in_reach
from inventory_tracking.macros.teleport import Way, landing
from inventory_tracking.macros.view import Viewport
from inventory_tracking.macros.world import NO_OWNER, World, monsters_and_dead
from inventory_tracking.native.layout import TILE_UNITS
from tests.inventory_tracking.scenarios.loop.helpers import (
    ASPECT,
    FIXTURE,
    CountedMemory,
    busiest_frame,
    monster_table,
    recorded_world,
)


ROUNDS = 5
PACKS = (5, 20, 60, 100)


def fastest(call: Callable[[], object], rounds: int = ROUNDS) -> float:
    """Milliseconds of the fastest of `rounds` calls."""
    best = math.inf
    for _ in range(rounds):
        began = time.perf_counter()
        call()
        best = min(best, time.perf_counter() - began)
    return best * 1000


def level_of(directory: Path) -> tuple[Ground, tuple[Room, ...], tuple[Walkable, ...]]:
    path = directory / 'level.json'
    with path.open() if path.exists() else gzip.open(directory / 'level.json.gz', 'rt') as handle:
        level = json.load(handle)
    grids = tuple(Walkable(**grid) for grid in level.get('ground', ()))
    rooms = tuple(Room(r['preset'], r['x'], r['y'], r['width'], r['height']) for r in level['rooms'])
    return Ground(grids), rooms, grids


def decision(seen: World, ground: Ground, hunter: Hunter | None = None) -> dict[str, float]:
    """The fight's own calls on one look at the world, in milliseconds, with what they worked on."""
    hunter = hunter or Hunter()
    player = seen.player
    assert player is not None
    here = (player.x, player.y)
    foes = hostiles(seen)
    reachable = [m for m in foes if in_reach(ground, here, (m.x, m.y), REACH, seen.doors)]
    near = [m for m in foes if math.dist(here, (m.x, m.y)) <= SIGHT]
    view = Viewport(ASPECT)
    companions = [m for m in seen.monsters if m.ally or m.owner != NO_OWNER]
    observed = observe(player, near, companions, ground, seen.doors, aimable=lambda f: view.reachable_focal(here, f))
    return {
        'hostiles': len(foes),
        'in sight': len(near),
        'reachable': len(reachable),
        'choose': fastest(lambda: hunter.choose(seen, foes, reachable or near[:1], ground, view)),
        'LinePolicy.choose': fastest(lambda: hunter.policy.choose(observed)),  # type: ignore[attr-defined]
        'observe': fastest(lambda: observe(player, near, companions, ground, seen.doors)),
        'in_reach over all': fastest(lambda: [in_reach(ground, here, (m.x, m.y), REACH, seen.doors) for m in foes]),
        'tough': fastest(lambda: hunter.tough(seen, reachable)),
    }


def main(directory: Path = FIXTURE) -> None:
    take = Take.load(directory)
    ground, rooms, grids = level_of(directory)
    frame = busiest_frame(take)
    print(f'{directory.name}: frame {frame["n"]}, {len(grids)} grids, {len(rooms)} rooms; ms, the fastest of {ROUNDS}')
    for count in PACKS:
        cost = decision(recorded_world(frame, count), ground)
        print(
            f'{count:4d} hostiles ({cost["in sight"]} in sight, {cost["reachable"]} reachable): '
            f'choose {cost["choose"]:.1f}  LinePolicy.choose {cost["LinePolicy.choose"]:.1f}  '
            f'observe {cost["observe"]:.2f}  in_reach over all {cost["in_reach over all"]:.2f}  '
            f'tough {cost["tough"]:.2f}  ({cost["choose"] / count:.2f} ms a hostile)'
        )
    seen = recorded_world(frame)
    assert seen.player is not None
    cost = decision(seen, ground)
    closed = sum(door.closed for door in seen.doors)
    print(
        f'the frame as recorded: {cost["hostiles"]} hostiles, {cost["in sight"]} in sight, {cost["reachable"]} '
        f'reachable, {closed} closed doors: choose {cost["choose"]:.1f}  '
        f'in_reach over all {cost["in_reach over all"]:.2f}'
    )
    here = (seen.player.x, seen.player.y)
    mobs = [(m.x, m.y) for m in hostiles(seen)]
    shots = fastest(lambda: [clear_shot(ground, here, mob, seen.doors) for mob in mobs])
    print(f'clear_shot: {shots / len(mobs) * 1000:.0f} us a shot ({len(mobs)} shots)')
    far = max(mobs, key=lambda mob: math.dist(mob, here))
    spots = firing_spots(ground, far, STRIKE_REACH, here, seen.doors)
    print(f'firing_spots: {fastest(lambda: firing_spots(ground, far, STRIKE_REACH, here, seen.doors)):.2f} ms')
    target = Target(
        seen.player.area, rooms, (far[0] / TILE_UNITS, far[1] / TILE_UNITS), 'the elite', 'hunt', False, grids
    )
    view = Viewport(ASPECT)
    way = Way(target, view)
    print(f'Way (a new mark: the potential over {len(way.cost)} tiles): {fastest(lambda: Way(target, view), 3):.1f} ms')
    print(
        f'landing (the spots in view, {len(spots)} firing spots known): '
        f'{fastest(lambda: landing(target, seen.player, way, ASPECT), 3):.1f} ms'
    )
    print(f'Ground(level grids): {fastest(lambda: Ground(grids)):.3f} ms')
    memory = CountedMemory()
    monster_table(memory, 0x100000, 60)
    monsters_and_dead(memory.read, 0x100000)
    print(f'monster walk, 60 live: {len(memory.reads)} reads ({(len(memory.reads) - 1) // 60} a monster and the heads)')


if __name__ == '__main__':
    main(*(Path(arg) for arg in sys.argv[1:2]))
