"""Compare explicit article-model routes by T5 spawns per ordinary kill, NOT per hour.

No time inputs, transit kills, revisits, population variation or weighted rooms.
All Heralds are assumed immediately killed without cost. See guides/terror_zones.html.
"""

import argparse
import itertools
import json
import random
from functools import cache
from pathlib import Path

from terror_zones.diagnostic import hazard


@cache
def probabilities(total: int, tier: int) -> tuple[float, ...]:
    return tuple(hazard(tier, 100 * k / total) for k in range(total))


@cache
def arrivals(total: int, tier: int) -> tuple[float, ...]:
    """Unconditional mass of the first success at each kill; index zero unused."""
    survival = 1.0
    mass = [0.0]
    for p in probabilities(total, tier):
        mass.append(survival * p)
        survival *= 1 - p
    return tuple(mass)


@cache
def continuation(total: int, tier: int, remaining: int, stop_after: int) -> tuple[float, float]:
    """Expected kills and T5 spawns after a local reset, with original denominator."""
    if remaining == 0 or probabilities(total, tier)[remaining - 1] == 0:
        return float(remaining), 0.0
    survival = 1.0
    kills = reward = 0.0
    for wait in range(1, remaining + 1):
        kills += survival
        mass = arrivals(total, tier)[wait]
        survival -= mass
        if mass == 0:
            continue
        reward += mass * (tier == 5)
        if tier > stop_after:
            more_kills, more_reward = continuation(total, min(5, tier + 1), remaining - wait, stop_after)
            kills += mass * more_kills
            reward += mass * more_reward
    return (float(remaining) if tier > stop_after else kills), reward


@cache
def zone_kernel(total: int, tier: int, stop_after: int) -> tuple[float, float, tuple[float, ...]]:
    """Transition through one fresh zone for leave-after-T1..T3 or T1..T4 policies."""
    if total < 1 or tier not in range(1, 6) or stop_after not in (3, 4):
        raise ValueError('positive population, tier 1..5, stop_after 3 or 4 required')
    kills, reward = continuation(total, tier, total, stop_after)
    terminal = [0.0] * 5
    if tier == 5:
        terminal[4] = 1.0
    else:
        success = sum(arrivals(total, tier))
        terminal[tier - 1] = 1 - success
        terminal[tier] = success
    return kills, reward, tuple(terminal)


def evaluate(zones: list[tuple[str, int]], stop_after: int) -> dict:
    state = [1.0, 0.0, 0.0, 0.0, 0.0]
    kills = reward = 0.0
    for _, total in zones:
        next_state = [0.0] * 5
        for tier, weight in enumerate(state, 1):
            cost, gain, terminal = zone_kernel(total, tier, stop_after)
            kills += weight * cost
            reward += weight * gain
            for i, probability in enumerate(terminal):
                next_state[i] += weight * probability
        state = next_state
    return {
        'mean_kills': kills,
        'mean_t5': reward,
        't5_per_1000_kills': 1000 * reward / kills if kills else 0,
        'probability_unlock_t5': state[4],
    }


def simulate(zones: list[tuple[str, int]], stop_after: int, rng: random.Random) -> tuple[int, int]:
    """Independent kill-by-kill Monte Carlo check, retaining failed progression."""
    tier = 1
    kills = reward = 0
    for _, total in zones:
        remaining = total
        since_spawn = 0
        while remaining:
            chance = probabilities(total, tier)[since_spawn]
            kills += 1
            remaining -= 1
            since_spawn += 1
            if rng.random() < chance:
                spawned_tier = tier
                reward += tier == 5
                tier = min(5, tier + 1)
                since_spawn = 0
                if spawned_tier <= stop_after:
                    break
    return kills, reward


def candidates(zones: list[tuple[str, int]], *, exhaustive: bool = False):
    if exhaustive:
        yield from ((f'permutation-{i}', list(route)) for i, route in enumerate(itertools.permutations(zones)))
    else:
        yield 'article-order', zones
        yield 'population-ascending', sorted(zones, key=lambda z: z[1])
        yield 'population-descending', sorted(zones, key=lambda z: z[1], reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=1000, help='independent simulation trials per selected route')
    parser.add_argument('--seed', type=int, default=20260921)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be positive')
    data = json.loads(Path(__file__).with_name('data').joinpath('article-zones.json').read_text())
    scenarios = {f'A{act}': [(name, n) for name, n in zones] for act, zones in data['acts'].items()}
    scenarios['ALL'] = [(f'Act {act}: {name}', n) for act, zones in data['acts'].items() for name, n in zones]
    output = {
        'date': '2026-09-21',
        'objective': 'T5 spawns per 1000 ordinary kills over a complete route; NOT Heralds/hour',
        'limitations': __doc__,
        'seed': args.seed,
        'runs': args.runs,
        'scenarios': {},
    }
    for name, zones in scenarios.items():
        comparisons = []
        routes = dict(candidates(zones, exhaustive=name == 'A4'))
        for order, route in routes.items():
            for stop_after in (3, 4):
                comparisons.append({'order': order, 'stop_after': stop_after, **evaluate(route, stop_after)})
        best = max(comparisons, key=lambda r: r['t5_per_1000_kills'])
        route = routes[best['order']]
        rng = random.Random(args.seed)
        observed = [simulate(route, best['stop_after'], rng) for _ in range(args.runs)]
        mean_kills = sum(k for k, _ in observed) / args.runs
        mean_reward = sum(r for _, r in observed) / args.runs
        output['scenarios'][name] = {
            'best_tested': best,
            'ordered_zones': route,
            'comparison_count': len(comparisons),
            'comparisons': comparisons,
            'simulation': {
                'mean_kills': mean_kills,
                'mean_t5': mean_reward,
                't5_per_1000_kills': 1000 * mean_reward / mean_kills if mean_kills else 0,
            },
        }
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
