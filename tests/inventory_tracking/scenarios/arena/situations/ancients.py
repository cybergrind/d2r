"""A low-danger pack of the Ancient's Way as a situation (rca/2026-10-14/run-1932-findings.md §4, the example of
22:50:26.9): the game of 22:32 on 2026-10-14 (take 20261014T194935Z-118, schema 4), from the landing at
(10265.5, 10611.5) at 22:50:27.0 for 20 s. The level run (KP_1, a terror zone's full clear) had just hopped toward
"clearing the way (10-12 near)": Bone Mages (624), Yetis (447) and Death Lords (606) standing in clumps, the nearest
15 to 22 units off, 36 hostiles within 60. In the game the character held there and struck from 17 to 22 units
(none within 10), every decision a Hold priced H 2 to 5 against a budget of about 640.

The arena's run is the goal mode's (the route to the Icy Cellar, fighting what stands within 30 on its way): the
terror zone's full clear needs the routes' progress, which the arena does not hold. The pack is the same either way.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.ancients [--cut] [--seeds 10]
"""

import argparse
import functools
import statistics
from collections.abc import Sequence

from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Situation, dump, load, once


NAME = 'ancients-way'
TAKE = '20261014T194935Z-118'
START, SECONDS = '2026-10-14T22:50:27.0+03:00', 20.0
ABOUT = "a low-danger pack 15 to 22 units off in the Ancient's Way, a level run (22:50, 2026-10-14)"


def cut() -> Situation:
    return from_take(
        TAKES / TAKE, START, SECONDS, name=NAME, reach=60.0,
        about=(
            "Ancient's Way, 2026-10-14 22:50:27: the level run landed 15 to 22 units from clumps of Bone Mages, Yetis "
            'and Death Lords and struck from there, 17 to 22 units off, none within 10 (run-1932-findings.md §4).'
        ),
    )  # fmt: skip


@functools.cache
def stored() -> Situation:
    return load(FIXTURES / f'{NAME}.json')


def variants() -> list[tuple[str, Situation, list | None]]:
    base = stored()
    run = [once('pickup')]
    return [
        ('KP_1 once: today', base, run),
        ('KP_1 once: new', base.logic('new'), run),
        ('attack mode alone: today', base, []),
        ('attack mode alone: new', base.logic('new'), []),
    ]


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
        kills = [len(situation.play(presses, seed=seed).kills) for seed in range(1, args.seeds + 1)]
        print(f'{label}: kills {kills}, median {statistics.median(kills)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
