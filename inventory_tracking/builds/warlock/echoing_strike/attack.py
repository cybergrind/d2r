"""Echoing Strike as the framework asks an attack (macros/build.py `Attack`): the skill the fight
holds, how far the blades hurt, what the strike reads off the character's own units, where to cast,
and what a cast takes off whom when a place to stand is priced. One decision for the simulator
(sim/engine.py) and for the game (combat/plan.md stage 5; the steer of 2026-10-10: the simulated gain
belonged to code the game never ran).

`LinePolicy`, the line sweep, is a policy (combat/policy.py `Policy`): through each live hostile within
REACH a virtual cast is laid along the line from the character, with the focal point on, short of and
past the monster (OFFSETS), and scored by the points the emulated blades would take off the monsters
where they stand: each contact is worth the blade's damage capped by what the monster has left (no
credit for overkill), with the duplicate rule, and a hit on a linked monster adds the share of its
damage to every other linked one, each capped by its own points. The best line is cast when it is
worth MIN_SCORE. It yields: while the player is moving it casts nothing (takeover with yield;
`yields=False` is the free variant the simulator scores for comparison).

`EchoingStrike` is that sweep with the rest of the contract on it:

- `aim`: the sweep's best line, and with `through` the best line laid through one of those units;
  both yield to a moving player and want MIN_SCORE;
- `sees`: the monsters the Defiler's Health Link holds, and the share of the damage dealt again;
- `dealt`: the line model a place is priced by, which is not `virtual_cast`: every monster ahead of
  the character within the blades' contact radius of the line to the focal point takes
  BLADES_A_CAST blades, up to the wall the blades stop at (the way out only, then).

They are two classes: the simulator, the scoreboard and the harnesses make sweeps of their own (not
yielding, leading, with a flat damage table) and score them as policies, with no skill and no
character's units in sight; `EchoingStrike.of` makes the attack of such a sweep.
"""

import math
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
from itertools import pairwise

from inventory_tracking.builds.warlock.echoing_strike.damage import DEFILER, damage_table, link_table
from inventory_tracking.builds.warlock.echoing_strike.hits import CONTACT_RADIUS
from inventory_tracking.builds.warlock.echoing_strike.mechanics import (
    BLADES,
    LIFE,
    OUT_FRAMES,
    RANGE,
    SPEED,
    cast,
    flown,
)
from inventory_tracking.builds.warlock.skills import ECHOING_STRIKE
from inventory_tracking.combat.policy import ELITE_WEIGHT, MIN_FOCAL, MIN_SCORE, Choice, Foe, Observation, Point
from inventory_tracking.macros.world import Monster


DUPLICATE = 1 / (2 * BLADES)  # skills.txt calc6 (100 / count) / 2: a cast's blades after the first on a monster and leg
REACH = RANGE  # units: a monster further than the blades fly is not a line
OFFSETS = (0.0, -3.0, 4.0)  # focal point along the line relative to the monster: on, short, past (ties: on)
# What one cast takes off a monster on its line, in blades: the first whole and the rest by the
# duplicate rule, out and back (`virtual_cast`: 2,800 points of a 1,000-point blade).
BLADES_A_CAST = 2.8
# The share of casts whose blades hit the monster aimed at, by its distance at the cast: (the bin's furthest units,
# the share). The Ancient's Way and Icy Cellar takes of 2026-10-14 (rca/2026-10-14/run-1932-findings.md §4.1,
# scripts/run1932_stand_casts.py: 694 aimed casts of five blades, standing and moving monsters together, as they
# were hit as often at the same distance). At the end of the blades' flight a monster's step is a miss.
HIT_BY_DISTANCE = ((6.0, 0.743), (10.0, 0.747), (14.0, 0.606), (18.0, 0.493), (REACH, 0.356))


# The bins' middles with their shares: what `hit_share` runs straight between.
HIT_MIDDLES = tuple(
    ((low + high) / 2, share)
    for (low, _), (high, share) in zip(((0.0, 0.0), *HIT_BY_DISTANCE), HIT_BY_DISTANCE, strict=False)
)


def hit_share(away: float) -> float:
    """`HIT_BY_DISTANCE` at `away` units: straight between the bins' middles, the end bins' own beyond them."""
    if away <= HIT_MIDDLES[0][0]:
        return HIT_MIDDLES[0][1]
    for (near, first), (far, second) in pairwise(HIT_MIDDLES):
        if away <= far:
            return first + (second - first) * (away - near) / (far - near)
    return HIT_MIDDLES[-1][1]


def engage_ring() -> float:
    """Units from a monster a stand is best at: where `hit_share` falls half way from its best (the casts close in)
    to its worst (the edge of the reach). Nearer, a step closer gains little; further, the hit share falls fast.
    13.9 from the takes of 2026-10-14, as the player engages (12 to 14 at the median, combat/policy.py)."""
    best = max(share for _, share in HIT_MIDDLES)
    half = (best + HIT_MIDDLES[-1][1]) / 2
    for (near, first), (far, second) in pairwise(HIT_MIDDLES):
        if first >= half > second:
            return near + (far - near) * (first - half) / (first - second)
    return REACH


ENGAGE = engage_ring()  # units: the firing ring an approach plans and the place a jump is best ended at


def virtual_cast(
    origin: Point,
    focal: Point,
    foes: dict[int, Foe],
    linked: frozenset[int] | set[int],
    share: float,
    damage_of: Callable[[int], float],
    radius: float = CONTACT_RADIUS,
    blocked: Callable[[Point], bool] | None = None,
    elite_weight: float = 1.0,
    lead: int | None = None,
) -> float:
    """Points one cast would take off the monsters where they stand (with `lead`, the frames from now
    to the blades' first frame: where each one's route has it as the blades fly), out and back: the duplicate
    rule, each contact capped by what the monster has left, and the link's spread to the other
    linked monsters, each capped by its own points; `blocked` are the walls the blades stop at. Points
    taken off an elite count `elite_weight` times (the worth of a line, not damage)."""
    left = {unit: foe.left for unit, foe in foes.items()}
    total = 0.0
    first: set[tuple[int, str]] = set()
    walkers = (
        {unit: [foe.ahead(lead + k) for k in range(LIFE)] for unit, foe in foes.items() if foe.route is not None}
        if lead is not None
        else {}
    )
    for path in cast(origin, focal, lambda k: origin, blocked):
        touched: set[tuple[int, str]] = set()
        for k, position in enumerate(path):
            leg = 'out' if k <= OUT_FRAMES else 'back'
            for unit, foe in foes.items():
                where = walkers[unit][k] if unit in walkers else foe.at
                if (unit, leg) in touched or left[unit] <= 0 or math.dist(position, where) > radius:
                    continue
                touched.add((unit, leg))
                dealt = damage_of(foe.txt) * (DUPLICATE if (unit, leg) in first else 1.0)
                first.add((unit, leg))
                taken = min(dealt, left[unit])
                left[unit] -= taken
                total += taken * (elite_weight if foe.elite else 1.0)
                if unit in linked:
                    for other in linked:
                        if other != unit and left.get(other, 0) > 0:
                            spread = min(dealt * share, left[other])
                            left[other] -= spread
                            total += spread * (elite_weight if foes[other].elite else 1.0)
    return total


def linked_set(defilers: Iterable[Point], foes: dict[int, Point], link_range: float, links: int) -> frozenset[int]:
    """The `links` live hostiles nearest a Defiler within its aura range: the ones Health Link holds."""
    posts = list(defilers)
    if not posts or not links:
        return frozenset()
    near = sorted((min(math.dist(post, at) for post in posts), unit) for unit, at in foes.items())
    return frozenset(unit for gap, unit in near[:links] if gap <= link_range)


@dataclass
class LinePolicy:
    yields: bool = True  # nothing while the player is moving
    reach: float = REACH
    offsets: tuple[float, ...] = OFFSETS
    damage_of: Callable[[int], float] = field(default_factory=damage_table)
    elite_weight: float = ELITE_WEIGHT
    # Frames from the decision to the blades' first frame: lines are laid and scored where the monsters'
    # routes have them as the blades fly. None: where they stand (the game's fight until it reads routes).
    lead: int | None = None

    def __call__(self, seen: Observation) -> Choice | None:
        if self.yields and seen.moving:
            return None
        best = self.choose(seen)
        return best if best is not None and best.worth >= MIN_SCORE else None

    def choose(self, seen: Observation, through: Collection[int] | None = None) -> Choice | None:
        """The best line through the live hostiles; with `through`, of the lines laid through those."""
        best: Choice | None = None
        for unit, foe in seen.foes.items():
            if through is not None and unit not in through:
                continue
            at = foe.at
            if self.lead is not None:  # through where it is when a blade gets as far as it stands now
                at = foe.ahead(self.lead + min(round(math.dist(at, seen.origin) / SPEED), OUT_FRAMES))
            away = math.dist(at, seen.origin)
            if away > self.reach or away == 0:
                continue
            ux, uy = (at[0] - seen.origin[0]) / away, (at[1] - seen.origin[1]) / away
            for offset in self.offsets:
                distance = max(MIN_FOCAL, min(away + offset, self.reach - 1))
                focal = (seen.origin[0] + ux * distance, seen.origin[1] + uy * distance)
                if seen.aimable is not None:
                    # The line is scored with the focal point the cast will have, not one off the screen
                    # that the aim would shorten after the choice (review.md, finding 8).
                    reached = seen.aimable(focal)
                    if reached is None:
                        continue
                    focal = reached
                worth = virtual_cast(
                    seen.origin, focal, seen.foes, seen.linked, seen.share, self.damage_of, blocked=seen.blocked,
                    elite_weight=self.elite_weight, lead=self.lead,
                )  # fmt: skip
                if worth > (best.worth if best is not None else 0.0):
                    best = Choice(focal, unit, worth)
        return best


@dataclass
class EchoingStrike(LinePolicy):
    """The strike of the Echoing Strike Warlock. `reach` is the blades' range (`LinePolicy.reach`)."""

    skill: int = ECHOING_STRIKE  # the skill whose input the fight holds
    engage: float = ENGAGE

    @classmethod
    def of(cls, policy: LinePolicy) -> EchoingStrike:
        """The attack of a line sweep made on its own (a test's or a harness's, with its damage table
        and its reach): the same sweep, as an attack."""
        return cls(**{part.name: getattr(policy, part.name) for part in fields(LinePolicy)})

    def sees(self, seen: Observation, companions: Sequence[Monster]) -> Observation:
        """A copy of the observation with the monsters the Defiler's Health Link holds, and the share
        of the damage dealt again to each other linked one."""
        link_range, links, share = link_table()
        defilers = [(c.x, c.y) for c in companions if c.txt_id == DEFILER]
        linked = linked_set(defilers, {unit: foe.at for unit, foe in seen.foes.items()}, link_range, links)
        return replace(seen, linked=linked, share=share)

    def aim(self, seen: Observation, through: Collection[int] = ()) -> Choice | None:
        """The best line worth MIN_SCORE, or None; nothing while the player is moving (`yields`).
        With `through`, the best of the lines laid through those units, whatever another is worth."""
        if not through:
            return self(seen)
        if self.yields and seen.moving:
            return None
        best = self.choose(seen, through=through)
        return best if best is not None and best.worth >= MIN_SCORE else None

    def dealt(
        self, origin: Point, focal: Point, foes: Mapping[int, Foe], blocked: Callable[[Point], bool] | None = None
    ) -> Mapping[int, float]:
        """The points a cast from `origin` at `focal` takes off each of `foes` on its line:
        BLADES_A_CAST blades off every one ahead of the character and within the contact radius of
        the straight line through the focal point, however far along it (the caller gives the ones
        in reach). Nothing from a focal point under the character. The blades stop at the first wall
        `blocked` says is on the line, as `virtual_cast`'s do (mechanics.py `flown`): one past it takes
        nothing, one before it the way out only, half the blades (run-2040-findings.md §3.3: 6% and 23%
        of the casts of the 23:40 game flew into walls, and a place was priced as if they came back)."""
        tx, ty = focal[0] - origin[0], focal[1] - origin[1]
        away = math.hypot(tx, ty)
        if not away:
            return {}
        ux, uy = tx / away, ty / away
        stop = flown(origin, focal, blocked)
        blades = BLADES_A_CAST if stop is None else BLADES_A_CAST / 2  # out and back, or out only
        hit = {}
        for unit, foe in foes.items():
            dx, dy = foe.at[0] - origin[0], foe.at[1] - origin[1]
            ahead = dx * ux + dy * uy
            if ahead > 0 and abs(dx * uy - dy * ux) <= CONTACT_RADIUS:
                if stop is not None and ahead > stop + CONTACT_RADIUS:
                    continue  # behind the wall the blades died in
                hit[unit] = self.damage_of(foe.txt) * blades
        return hit

    def lands(self, away: float) -> float:
        """The share of casts that hit a monster `away` units off, against the casts close in (`hit_share` over its
        best): 1.0 within 10 units, about 0.48 at the end of the reach."""
        return hit_share(away) / max(share for _, share in HIT_MIDDLES)


ECHOING_STRIKE_ATTACK = EchoingStrike()  # the build's: the sweep as the game runs it, with the build's damage table
