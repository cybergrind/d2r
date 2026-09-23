"""Article-model diagnostic, NOT a validated game emulator or route optimizer.

Assumes fully populated, equally weighted monsters; original population denominator;
pre-kill completion; local counter reset on successful roll; immediate spawn and
tier advancement; no Herald/minion kills. These assumptions need runtime validation.
Parameters transcribed from the saved Patch 3.2 article on 2026-09-21.
"""

import argparse
import json
import math
import random


# slope, midpoint, asymptote, vertical shift; equation output is a percentage.
PARAMETERS = {
    1: (0.04, 56, 10, -4.6),
    2: (0.04, 44, 7, -3.4),
    3: (0.04, 44, 7, -3.4),
    4: (0.05, 47, 4, -1.2),
    5: (0.08, 42, 2.5, -0.13),
}


def hazard(tier: int, completion: float, *, floor_percent: bool = False) -> float:
    """Probability of one successful roll, with zero base chance assumed."""
    if tier not in PARAMETERS or not math.isfinite(completion) or not 0 <= completion <= 100:
        raise ValueError('tier must be 1..5 and completion must be finite and within 0..100')
    m, midpoint, asymptote, shift = PARAMETERS[tier]
    x = math.floor(completion) if floor_percent else completion
    return max(0.0, min(1.0, (asymptote / (1 + math.exp(-m * (x - midpoint))) + shift) / 100))


def validate(total: int, tier: int, remaining: int | None) -> int:
    remaining = total if remaining is None else remaining
    if total < 1 or tier not in PARAMETERS or not 0 <= remaining <= total:
        raise ValueError('positive total, tier 1..5 and remaining within 0..total required')
    return remaining


def first_spawn(total: int, tier: int, remaining: int | None = None, *, floor_percent: bool = False) -> dict:
    """Exact finite first-spawn distribution starting with zero progress.

    Failure is retained as probability mass, not treated as a spawn at exhaustion.
    'remaining' models leftovers immediately after a counter reset.
    """
    remaining = validate(total, tier, remaining)
    survival = 1.0
    weighted_kills = spent = 0.0
    for killed in range(remaining):
        spent += survival
        p = hazard(tier, 100 * killed / total, floor_percent=floor_percent)
        weighted_kills += (killed + 1) * survival * p
        survival *= 1 - p
    success = 1 - survival
    return {
        'spawn_probability': success,
        'no_spawn_probability': survival,
        'conditional_mean_kills': weighted_kills / success if success else None,
        'expected_kills_until_spawn_or_exhaustion': spent,
    }


def simulate_zone(
    total: int, tier: int, rng: random.Random, remaining: int | None = None, *, floor_percent: bool = False
) -> list[tuple[int, int]]:
    """Roll once per kill; return (kill number, spawned tier) for each success."""
    remaining = validate(total, tier, remaining)
    since_spawn = 0
    events = []
    for kill in range(1, remaining + 1):
        p = hazard(tier, 100 * since_spawn / total, floor_percent=floor_percent)
        since_spawn += 1
        if rng.random() < p:
            events.append((kill, tier))
            tier = min(5, tier + 1)
            since_spawn = 0
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--monsters', type=int, required=True)
    parser.add_argument('--tier', type=int, default=1)
    parser.add_argument('--remaining', type=int)
    parser.add_argument('--runs', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=20260921)
    parser.add_argument('--floor-percent', action='store_true')
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be positive')
    try:
        exact = first_spawn(args.monsters, args.tier, args.remaining, floor_percent=args.floor_percent)
    except ValueError as error:
        parser.error(str(error))
    rng = random.Random(args.seed)
    totals = dict.fromkeys(range(1, 6), 0)
    first_successes = 0
    for _ in range(args.runs):
        events = simulate_zone(args.monsters, args.tier, rng, args.remaining, floor_percent=args.floor_percent)
        first_successes += bool(events)
        for _, tier in events:
            totals[tier] += 1
    print(
        json.dumps(
            {
                'model': 'unvalidated article approximation; no time or route optimization',
                'inputs': vars(args),
                'exact_first_spawn': exact,
                'simulated_first_spawn_probability': first_successes / args.runs,
                'simulated_mean_spawns_by_tier': {tier: n / args.runs for tier, n in totals.items()},
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
