"""Pure exposure pricing, in life points, for a place, dwell and weapon set.

Rules/tables are shared with sim.casters, not fitted head counts. The four read AIs
use their cast/swing branches, cadence, missile range and damage. Other AIs use
an explicitly conservative table-melee/pooled-shot stand-in. Short seeded event
rollouts retain correlated bursts and curses; they are not server predictions.
See rca/2026-10-13/safety-pricing.md for uncertainty and live observation limits.
"""

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Literal

from inventory_tracking.combat.policy import Point, clear_line
from inventory_tracking.combat.sim import casters as rules
from inventory_tracking.combat.sim.guard import GuardRule
from inventory_tracking.combat.sim.monsters import Traits, shoots
from inventory_tracking.combat.survival import Pressure, Supply
from inventory_tracking.config import Config, Percent, Positive
from inventory_tracking.terror.danger import table as threat_table


Hands = Literal['battle', 'travel']
KINDS = ('physical', 'fire', 'lightning', 'cold', 'poison', 'magic')
# monstats deathDmg, verified in scenarios/threat/threat_table.json (2026-10-13).
# A corpse already struck by a projectile can explode before another look.
EXPLODING = frozenset((214, 215, 216, 441, 442, 443, 690, 691))


class SafetySettings(Config):
    floor: Percent = 65.0  # Q1/Q6: life is a hard constraint, potions are not borrowed life
    insist_floor: Percent = 40.0
    insist_per_second: Positive = 5.0
    horizon: Positive = 1.5
    veto_share: Percent = 5.0
    healing_seconds: Positive = 4.0  # Q6, seconds per potion
    rejuvenation_seconds: Positive = 20.0
    healing_points: Positive = 480.0  # named stand-in until the belt's potion quality is priced
    commit_share: Positive = 0.20  # Q2, improvement required to leave a firing stand
    commit_seconds: Positive = 0.30
    fight_through: bool = True  # Q3: allow a strike to advance a pressed goal
    middle_detour: Positive = 6.0  # Q4; the middle leash itself belongs to steps 8-9
    recharge_notice: int = 20  # Q5; never an instruction to recharge
    press_enables_attack: bool = False  # Q7, intent remains the runner's
    middle_objects_need_press: bool = True  # Q8
    trials: int = 64
    seed: int = 61013  # same facts, same samples, independent of process hash/random state
    companion_uncertainty: float = 0.15  # nearest wins; companion motion is unobserved over the dwell
    unknown_damage_factor: Positive = 3.0  # unknown AI/Diablo: table blow, conservative burst factor
    unknown_period: Positive = 1.0
    unknown_points: Positive = 500.0  # no table row: up to 1500 after the conservative burst factor
    corpse_radius: Positive = 5.0
    move_overhead: Positive = 0.5
    hold_dwell: Positive = 0.72
    landing_dwell: Positive = 0.36  # following decision and residual cast delay, separate from transit
    operate_dwell: Positive = 1.5


@dataclass(frozen=True)
class Protection:
    # Raw percentages AFTER difficulty penalty, BEFORE cap. Curses already on the
    # character belong in these stats, so only future curses are added below.
    resists: tuple[tuple[str, float], ...] = ()
    block: float = 0.0
    defence: float = 0.0
    level: int = 94
    flat: tuple[tuple[str, float], ...] = ()
    absorb: tuple[tuple[str, float], ...] = ()
    guard: GuardRule | None = None
    pool: float = 0.0  # lower bound only: the client does not receive pool decrements


@dataclass(frozen=True)
class Hostile:
    unit: int
    txt: int
    at: Point
    flags: int = 0
    modifiers: tuple[int, ...] = ()
    tier: int = 0
    level: int | None = None
    active: bool = False
    stunned: float = 0.0
    life: float = 1.0


@dataclass(frozen=True)
class Look:
    hostiles: tuple[Hostile, ...]
    companions: tuple[Point, ...] = ()
    battle: Protection = Protection()
    travel: Protection = Protection()
    life: float = math.inf
    blocked: Callable[[Point], bool] | None = field(default=None, compare=False)
    # Extra bars supplied by build tactics, independent of the budget.
    barred: Callable[[Point], bool] | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Harm:
    mean: float = 0.0
    worst: float = 0.0
    by: tuple[tuple[int, float], ...] = ()
    losses: tuple[float, ...] = ()
    barred: str | None = None
    stand_ins: tuple[int, ...] = ()


@dataclass(frozen=True)
class Exposure:
    unit: int
    blows: float
    chance: float
    parts: tuple[tuple[str, float, float], ...]
    melee: bool = False


@lru_cache(maxsize=4096)
def traits(txt: int, level: int | None, flags: int, mods: tuple[int, ...], tier: int) -> Traits:
    return Traits.of(txt, level, flags, mods, tier)


def exposure(seen: Look, place: Point, dwell: float, protection: Protection, settings: SafetySettings):
    """A*w*n*hit*points, retaining each burst as one event (flames correlate)."""
    found: list[Exposure] = []
    unknown: list[int] = []
    curses = 0.0
    for m in sorted(seen.hostiles, key=lambda m: m.unit):
        events, curse_rate, stand_ins = hostile_exposure(m, seen, place, dwell, protection, settings)
        found.extend(events)
        curses += curse_rate
        unknown.extend(stand_ins)
    return tuple(e for e in found if e.blows > 0 and e.chance > 0), 1 - math.exp(-curses), tuple(sorted(set(unknown)))


def hostile_exposure(
    m: Hostile, seen: Look, place: Point, dwell: float, protection: Protection, settings: SafetySettings
):
    """One hostile's AI branches, evaluated immediately against one immutable look."""
    found: list[Exposure] = []
    unknown: list[int] = []
    curses = 0.0
    d = rules.ai_distance(m.at, place)
    near = min((rules.ai_distance(m.at, p) for p in seen.companions), default=math.inf)
    if min(d, near) >= rules.RADIUS or (not m.active and not clear_line(seen.blocked, m.at, place)):
        return (), 0.0, ()
    share = 1.0 if d <= near else settings.companion_uncertainty
    t = max(0.0, dwell - m.stunned)
    if t <= 0:
        return (), 0.0, ()
    row = rules.row_of(m.txt)
    model = traits(m.txt, m.level, m.flags, m.modifiers, m.tier)
    ai = rules.mind_of(m.txt)
    speed = rules.speed_of(row) * 25 if row else model.speed * 25
    delay = rules.number(row, 'aidel(H)', 15) if row else 13
    # Reach during the dwell. A monster spends the approach time walking, not striking.
    melee_time = max(0.0, t - max(0.0, d - rules.REACH) / max(speed, 0.1))

    def swing(chance=1.0):
        frames = rules.MODE_FRAMES.get((ai, 'A1'), 12) if ai else 12
        period = (frames + delay) / 25 if ai else settings.unknown_period
        hit = rules.hit_chance(row, model.level, protection.defence, protection.level) if row else 0.95
        parts = [('physical', *model.damage)]
        if not ai and model.damage[1] <= 0:
            parts = [('physical', settings.unknown_points / 2, settings.unknown_points)]
        parts += [(k, model.damage[0] * lo, model.damage[1] * hi) for k, lo, hi in model.elements]
        if not ai:
            parts = [
                (k, lo * settings.unknown_damage_factor, hi * settings.unknown_damage_factor) for k, lo, hi in parts
            ]
        found.append(
            Exposure(m.unit, melee_time / period * chance, share * hit * (1 - protection.block), tuple(parts), True)
        )

    def missile(mid: int, slot: int, count: float, reach: float, chance: float, cooldown: float = 0.0):
        assert row is not None
        assert ai is not None
        moving = max(0.0, d - reach) / max(speed, 0.1)
        active = max(0.0, t - moving)
        distance = min(d, reach)
        mr = rules.missile_row(mid)
        if distance > rules.missile_step(mid) * rules.number(mr, 'Range') + rules.CONTACT:
            return
        level = rules.skill_level(row, slot)
        parts = []
        for k, (lo, hi) in rules.missile_damage(mid, level).items():
            # Reserve the full poison duration at impact. This deliberately
            # overprices damage after the look, but does not forget it when a
            # trajectory is split or an afflicted character leaves missile range.
            length = rules.number(mr, 'ELen') if k == 'poison' else 1.0
            parts.append((k, lo * count * length, hi * count * length))
        period = max((rules.MODE_FRAMES[ai, 'S1'] + delay) / 25, cooldown)
        found.append(Exposure(m.unit, active / period * chance, share, tuple(parts)))

    if ai == rules.FINGER_MAGE:
        assert row is not None
        close = d <= rules.REACH
        swing(rules.number(row, 'aip1(H)') / 100 if close else 0.0)
        chance = rules.number(row, 'aip2(H)') / 100 * (0.4 if close else 1.0)
        missile(177, 1, 1.0, rules.number(row, 'aip5(H)'), chance)
    elif ai == rules.DOOM_KNIGHT:
        swing()
        # El1 rand at 60%; mean element mix, spread retained in the blow.
        if found and row:
            scale = model.damage[1] / max(rules.number(row, 'A1MaxD(H)'), 1.0)
            extra = tuple((k, 0.0, rules.number(row, 'El1MaxD(H)') * scale * 0.6 / 2) for k in rules.RANDOM_ELEMENTS)
            e = found[-1]
            found[-1] = Exposure(e.unit, e.blows, e.chance, e.parts + extra, True)
    elif ai == rules.OBLIVION_KNIGHT:
        assert row is not None
        reach = rules.number(row, 'aip2(H)')
        if d < reach:
            curses += t / (rules.number(row, 'aip3(H)') / 25)  # cooldown caps future curse rate
        chance = rules.number(row, 'aip5(H)') / 100
        bone = rules.number(row, 'aip6(H)') / 100
        missile(rules.BONE_SPIRIT, 3, 1.0, reach, chance * bone)
        for mid in rules.BOLTS:
            missile(mid, 1, 1.0, reach, chance * (1 - bone) / len(rules.BOLTS))
    elif ai == rules.MEGADEMON:
        assert row is not None
        close = d <= rules.REACH
        chance = rules.number(row, 'aip2(H)' if close else 'aip1(H)') / 100
        count = len(range(rules.RELEASE[ai, 'S1'], rules.MODE_FRAMES[ai, 'S1'], rules.FLAME_GAP))
        missile(675, 1, count, rules.skill_level(row, 1), chance, rules.number(row, 'aip6(H)') / 25)
        swing((1 - chance) * rules.number(row, 'aip3(H)') / 100)
    else:
        unknown.append(m.txt)
        threat = threat_table().monsters.get(m.txt)
        if shoots(m.txt) or (threat is not None and threat.ranged):
            # Pooled shot is explicitly a fallback, not a claim to have read this AI.
            points = max(model.damage[1], 100.0) * settings.unknown_damage_factor
            kind = min(KINDS, key=lambda k: dict(protection.resists).get(k, 0.0))
            found.append(Exposure(m.unit, t / settings.unknown_period, share, ((kind, points / 2, points),)))
        else:
            swing()
    return tuple(found), curses, tuple(unknown)


def approach(seen: Look, place: Point, elapsed: float) -> Look:
    """Project pursuit during a leg; actors do not freeze while weapons are swapped.

    Nearest target and table walking speed are known. A melee approach is the
    conservative branch for mixed melee/casting AIs; ranged AIs stop at cast range.
    Walls stop this straight local projection. No unseen actor is invented.
    """
    moved = []
    for m in seen.hostiles:
        target = min((place, *seen.companions), key=lambda p: rules.ai_distance(m.at, p))
        distance = rules.ai_distance(m.at, target)
        row, ai = rules.row_of(m.txt), rules.mind_of(m.txt)
        reach = rules.REACH
        if row and ai in (rules.FINGER_MAGE, rules.OBLIVION_KNIGHT):
            reach = rules.number(row, 'aip5(H)' if ai == rules.FINGER_MAGE else 'aip2(H)')
        speed = rules.speed_of(row) * 25 if row else traits(m.txt, m.level, m.flags, m.modifiers, m.tier).speed * 25
        travel = min(max(0.0, distance - reach), speed * max(0.0, elapsed - m.stunned))
        if travel and distance and (m.active or distance < rules.RADIUS):
            fraction = min(1.0, travel / max(math.dist(m.at, target), 1e-9))
            point = (m.at[0] + (target[0] - m.at[0]) * fraction, m.at[1] + (target[1] - m.at[1]) * fraction)
            if clear_line(seen.blocked, m.at, point):
                m = replace(m, at=point)
        moved.append(m)
    return replace(seen, hostiles=tuple(moved))


def harm(seen: Look, place: Point, dwell: float, hands: Hands, settings: SafetySettings | None = None) -> Harm:
    return harm_path(seen, ((place, dwell, hands),), settings)


def harm_path(seen: Look, path: tuple[tuple[Point, float, Hands], ...], settings: SafetySettings | None = None) -> Harm:
    """One event clock over a trajectory; only its final stand is tactically barred.

    Splitting a walk into integration slices must not restart a hostile's burst
    on every slice. The fractional attack phase carries across places and hands.
    """
    settings = settings or SafetySettings()
    if not path:
        return Harm()
    phases = []
    unknown = set()
    uncursed = 1.0
    for index, (place, dwell, hands) in enumerate(path):
        protection = seen.battle if hands == 'battle' else seen.travel
        events, cursed, stand_ins = exposure(seen, place, max(0.0, dwell), protection, settings)
        phases.append((events, protection))
        uncursed *= 1 - cursed
        unknown.update(stand_ins)
        if index + 1 < len(path):
            seen = approach(seen, place, dwell)
    place, dwell, _ = path[-1]
    barred = 'a tactic bars this place' if seen.barred is not None and seen.barred(place) else None
    if dwell > 0 and any(m.txt in EXPLODING and math.dist(m.at, place) < settings.corpse_radius for m in seen.hostiles):
        barred = 'an exploding corpse can reach this place'
    if not any(events for events, _ in phases):
        return Harm(barred=barred, stand_ins=tuple(sorted(unknown)))
    rng = random.Random(settings.seed)
    losses: list[float] = []
    totals: dict[int, float] = {}
    # A curse is shared by all blows in a rollout. No healing promised in advance.
    for _ in range(settings.trials):
        curse = rng.randrange(3) if rng.random() < 1 - uncursed else -1
        pool = phases[0][1].pool
        clocks: dict[tuple, float] = {}
        loss = 0.0
        for events, protection in phases:
            resists, flat, absorb = dict(protection.resists), dict(protection.flat), dict(protection.absorb)
            for event in events:
                key = (event.unit, event.parts, event.melee)
                if key not in clocks:
                    clocks[key] = rng.random()
                before = clocks[key]
                clocks[key] += event.blows
                count = math.floor(clocks[key]) - math.floor(before)
                for _ in range(count):
                    if rng.random() >= event.chance:
                        continue
                    points = 0.0
                    for kind, low, high in event.parts:
                        raw = rng.uniform(low, high)
                        if protection.guard is not None and kind in protection.guard.kinds:
                            taken = min(pool, raw)
                            pool -= taken
                            raw -= taken
                        delta = (
                            (-100 if curse == 0 else -50 if curse == 1 else 0)
                            if kind == 'physical'
                            else (-55 if curse == 2 and kind not in ('magic',) else 0)
                        )
                        resistance = min(
                            50.0 if kind == 'physical' else 75.0, max(-100.0, resists.get(kind, 0.0) + delta)
                        )
                        after = max(0.0, raw - flat.get(kind, 0.0)) * (1 - resistance / 100)
                        points += max(0.0, after - min(after, absorb.get(kind, 0.0)))
                    loss += points
                    totals[event.unit] = totals.get(event.unit, 0.0) + points
        losses.append(loss)
    mean = sum(losses) / len(losses)
    worst = max(mean, sorted(losses)[min(len(losses) - 1, math.ceil(0.95 * len(losses)) - 1)])
    return Harm(
        mean,
        worst,
        tuple(sorted(((u, v / len(losses)) for u, v in totals.items()), key=lambda r: (-r[1], r[0]))),
        tuple(losses),
        barred,
        tuple(sorted(unknown)),
    )


def veto(priced: Harm, life: float, settings: SafetySettings | None = None) -> str | None:
    settings = settings or SafetySettings()
    if priced.barred:
        return priced.barred
    if priced.losses and sum(loss >= life for loss in priced.losses) / len(priced.losses) > settings.veto_share / 100:
        return 'lethal exposure in the short rollouts'
    return None


def blockers(priced: Harm, allowance: float) -> tuple[int, ...]:
    """Contributors to remove, largest first, to bring the estimated tail under budget.

    Tail shares use the same proportional attribution as the mean. The complete
    price and veto are recomputed after a death; removing a name grants no credit.
    """
    left = priced.worst
    found = []
    for unit, points in priced.by:
        if left <= allowance:
            break
        found.append(unit)
        left -= points * priced.worst / max(priced.mean, 1e-9)
    return tuple(found)


def budget(life: float, most: float, pressure: Pressure, settings: SafetySettings, *, insisting: float = 0.0) -> float:
    floor = max(settings.insist_floor, settings.floor - max(0.0, insisting) * settings.insist_per_second)
    return max(0.0, life - floor / 100 * most) * (1 - min(1.0, pressure.rate * settings.horizon))


def life_price(supply: Supply, most: float, settings: SafetySettings) -> float:
    if supply.healing:
        return settings.healing_seconds / settings.healing_points
    return settings.rejuvenation_seconds / max(most, 1.0)
