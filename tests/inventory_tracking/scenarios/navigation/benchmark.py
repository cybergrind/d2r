"""The route situations as a table, and the same planner over routes drawn at random on their levels.

    uv run --offline python -m tests.inventory_tracking.scenarios.navigation.benchmark       # the fixtures
    uv run --offline python -m tests.inventory_tracking.scenarios.navigation.benchmark 20    # and 20 routes a level

A random route is two spots with footing on one of the fixtures' levels, the same ones every run. The
table says how many hops the production planner made, how many the reference needs, where hops were
made that took nothing off the reference's count, and what the planner's own work cost a hop.
"""

import random
import sys
from collections import Counter
from dataclasses import replace

from tests.inventory_tracking.scenarios.navigation.harness import (
    Situation,
    Trip,
    footing_of,
    load,
    names,
    run_production,
)


def random_routes(count: int, seed: int = 20261010) -> list[Situation]:
    """`count` routes on each of the fixtures' distinct levels, between spots with footing."""
    found, seen = [], set()
    pick = random.Random(seed)
    for name in names():
        base = load(name)
        if base.ground in seen or base.hidden:
            continue
        seen.add(base.ground)
        footing = footing_of(base.ground)
        spots = [
            (footing.x + column + 0.5, footing.y + row + 0.5)
            for row in range(footing.height)
            for column in range(footing.width)
            if footing.cells[row] >> column & 1
        ]
        for number in range(count):
            start, mark = pick.sample(spots, 2)
            found.append(replace(base, name=f'{name}#{number}', start=start, mark=mark, recorded_hops=None))
    return found


def totals(trips: list[Trip]) -> str:
    made = [trip for trip in trips if trip.arrived and trip.reference is not None]
    hops, fewest = sum(trip.presses for trip in made), sum(trip.reference for trip in made)
    over = Counter(trip.over for trip in made)
    seconds = sum(trip.planning for trip in trips) / max(sum(trip.presses for trip in trips), 1)
    return (
        f'{len(trips)} routes, {len(trips) - len(made)} not arrived; {hops} hops against {fewest} by the reference '
        f'({100 * (hops - fewest) / max(fewest, 1):.1f}% over); routes by hops over: {dict(sorted(over.items()))}; '
        f'{seconds * 1000:.0f} ms of planning a hop'
    )


def main(count: int = 0) -> None:
    trips = [run_production(load(name)) for name in names()]
    for trip in trips:
        lost = ', '.join(f'hop {number} ({had} left before, {has} after)' for number, _, had, has in trip.lost())
        print(
            trip.line()
            + (f'; nothing gained by {lost}' if lost else '')
            + (f'; {trip.stopped}' if trip.stopped else '')
        )
    print('the fixtures: ' + totals(trips))
    if count:
        print('random routes: ' + totals([run_production(route) for route in random_routes(count)]))


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
