"""Herald odds as the game computes them (D2R.exe, read 2026-10-03; terror/plan.md item 6).

A level's completion is (populated rooms / rooms in the level) x (kills / hostile monsters
spawned so far); the group's is the weighted mean over its levels (`zone_completion_weight`),
in percent, not floored. A Herald stores the group's completion when it spawns; the next roll
uses the completion above that. Every kill is counted first and then rolls once at the new
completion. That level completion equals kills / (spawned / room share): the game extrapolates
a level's population from the rooms seen, and the kills ahead are projected the same way,
current level first, then the group's other levels in table order. The curve is the article's
(terror_zones/diagnostic.py), whose parameters equal the game file's.
"""

import math
from dataclasses import dataclass

from terror_zones.diagnostic import PARAMETERS, hazard


@dataclass(frozen=True)
class Level:
    weight: float
    killed: int  # hostile kills this game: these mobs stay dead
    spawned: int  # hostile monsters seen there (the game: spawned so far)
    populated: int  # rooms loaded so far
    rooms: int | None  # the level's room count, None before entering it
    prior: float  # population to assume where nothing tells better (the article's share)

    @property
    def population(self) -> float:
        if self.rooms is None:
            estimate = max(self.prior, self.spawned)
        elif self.rooms == 0:
            estimate = self.spawned
        elif self.populated == 0 or self.spawned == 0:
            estimate = self.prior
        else:
            estimate = self.spawned * self.rooms / min(self.populated, self.rooms)
        return max(estimate, self.killed)

    def completion(self, ahead: int = 0) -> float:
        population = self.population
        return (self.killed + ahead) / population if population else 0.0


@dataclass(frozen=True)
class Odds:
    tier: int  # the tier that spawns next
    completion: float  # percent above the completion stored at the group's last Herald
    breakpoint: float  # first completion with a chance for this tier
    kills_to_breakpoint: int | None  # kills before the first that can roll a Herald; None: out of reach
    reachable: float  # completion if every mob left is killed
    remaining: int  # mobs left alive in the group
    next_kill: float
    over_remaining: float  # at least one spawn if every remaining mob is killed


def chance(tier: int, completion: float) -> float:
    return hazard(tier, min(100.0, max(0.0, completion)))


def breakpoint(tier: int) -> float:
    slope, midpoint, asymptote, shift = PARAMETERS[tier]
    return midpoint - math.log(asymptote / -shift - 1) / slope


def group_completion(levels: list[Level], ahead: list[int] | None = None) -> float:
    ahead = ahead or [0] * len(levels)
    total = sum(level.weight for level in levels)
    done = sum(level.weight * level.completion(more) for level, more in zip(levels, ahead, strict=True))
    return 100 * done / total if total else 0.0


def odds(tier: int, levels: list[Level], current: int = 0, offset: float = 0.0) -> Odds:
    left = [max(0, round(level.population) - level.killed) for level in levels]
    ahead = [0] * len(levels)
    order = [current, *(index for index in range(len(levels)) if index != current)]
    start = group_completion(levels) - offset
    reach, first, miss, kills = None, 0.0, 1.0, 0
    for index in order:
        for _ in range(left[index]):
            ahead[index] += 1
            roll = chance(tier, group_completion(levels, ahead) - offset)
            if kills == 0:
                first = roll
            if roll > 0 and reach is None:
                reach = kills
            miss *= 1 - roll
            kills += 1
    return Odds(
        tier=tier,
        completion=max(0.0, start),
        breakpoint=breakpoint(tier),
        kills_to_breakpoint=reach,
        reachable=max(0.0, group_completion(levels, ahead) - offset),
        remaining=sum(left),
        next_kill=first,
        over_remaining=1 - miss,
    )
