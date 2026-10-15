"""The Icy Cellar's door from the Ancient's Way with the staff empty, as a situation
(rca/2026-10-14/run-1932-findings.md
§1, rca/2026-10-14/navigation-classes.md): the game of 22:32 on 2026-10-14 (take 20261014T194935Z-118, schema 4),
from 22:54:13.0 for 46 s, the Teleport staff at 0 charges all session (every jump a Blade Warp), attack mode on.

What happened there. A full clear of the terror zone passed an unexplored room for "no strike in 10 s" after a run of
153 units toward it, and the room came back under a new tile key 5 units on: 8 warps between B and C in 9.6 s
(§1.2.1). Then 25 presses of the teleport key: the press was handed to the old step, which with the staff empty
walked toward a place a Teleport would land on, into the pocket D 43 units from the door in a straight line and 276
by the walked way, and stopped there three times on "no Blade Warp or walk leads toward Icy Cellar" (§1.2.2). The
player walked the way by hand (north to y 10678, west to x 10060 and back, 280 units in 16 s).

The places (world units): A, where the window begins; B and C, the two ends of the back and forth; D, the pocket;
DOOR, the Icy Cellar mark. The way from D goes round the wall at x 10150-10168: the arena's ground is the take's.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.ancients_door [--cut] [--seeds 3]
"""

import argparse
import functools
import math
from collections.abc import Sequence
from dataclasses import replace

from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Situation, dump, held, load


NAME = 'ancients-door'
TAKE = '20261014T194935Z-118'
START, SECONDS = '2026-10-14T22:54:13.0+03:00', 46.0
REACH = 320.0  # units round A the ground is kept: the walked way from D to the door goes 280 round the wall
ABOUT = "the Icy Cellar's door from the Ancient's Way with the staff empty: the back and forth and the pocket (22:54)"
A, B, C, D = (10193.5, 10573.5), (10189.5, 10654.5), (10209.5, 10642.5), (10172.5, 10729.5)
DOOR = (10130.0, 10727.5)  # the Icy Cellar mark, (2026, 2145.5) in tiles
POCKET = 12.0  # units from D: in the pocket
AT_DOOR = 10.0  # units from the mark: the door's click is the route step's from here (teleport.py NEAR_WARP)


def cut() -> Situation:
    return from_take(
        TAKES / TAKE, START, SECONDS, name=NAME, reach=REACH,
        about=(
            "Ancient's Way, 2026-10-14 22:54:13: the staff empty, a full clear that went back and forth between an "
            "unexplored room and the Icy Cellar's door, then 25 presses of the teleport key that walked into a pocket "
            '276 units by the walked way from the door (run-1932-findings.md §1).'
        ),
    )  # fmt: skip


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def standing(situation: Situation, at: tuple[float, float]) -> Situation:
    """A copy with the character at `at` (the take's character otherwise)."""
    found = situation.variant()
    found.scene.hero = replace(found.scene.hero, at=at)
    return found


def variants() -> list[tuple[str, Situation, list | None]]:
    """The teleport key held from the pocket D and from B, the staff empty, by the pursuit loop (the live game's) and
    by today's keys; the recording's own presses after a level run's press."""
    base = stored()
    key = [held('teleport', every=0.3)]
    return [
        ('KP_4 held from the pocket: new', standing(base, D).logic('new'), key),
        ('KP_4 held from the pocket: today', standing(base, D), key),
        ('KP_4 held from B: new', standing(base, B).logic('new'), key),
        ('KP_4 held from B: today', standing(base, B), key),
        ('as recorded: new', base.logic('new'), None),
    ]


def first_at_door(track: Sequence[tuple[float, float, float]]) -> float | None:
    """The first time the character stood within AT_DOOR of the door's mark."""
    return next((at for at, x, y in track if math.dist((x, y), DOOR) <= AT_DOOR), None)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help='cut the fixture again from the take')
    parser.add_argument('--seeds', type=int, default=3)
    args = parser.parse_args(argv)
    if args.cut:
        FIXTURES.mkdir(exist_ok=True)
        dump(cut(), FIXTURES / f'{NAME}.json')
        stored.cache_clear()
    for label, situation, presses in variants():
        for seed in range(1, args.seeds + 1):
            outcome = situation.play(presses, seed=seed)
            end = outcome.track[-1]
            print(
                f'{label} seed {seed}: at the door {first_at_door(outcome.track)}, end ({end[1]:.0f}, {end[2]:.0f}) '
                f'{math.dist(end[1:], DOOR):.0f} from it, moved {outcome.moved:.0f}, dead {outcome.dead_at}, '
                f'stage {outcome.stage}, said "no way" '
                f'{sum("no way" in t or "leads toward" in t for _, t in outcome.said)}'
            )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
