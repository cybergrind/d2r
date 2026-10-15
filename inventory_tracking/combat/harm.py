"""Pure exposure pricing, in life points, for a place, dwell and weapon set.

Rules/tables are shared with sim.casters, not fitted head counts. The four read AIs
use their cast/swing branches, cadence, missile range and damage. Other AIs use
an explicitly conservative table-melee/pooled-shot stand-in. Short seeded event
rollouts retain correlated bursts and curses; they are not server predictions.
See rca/2026-10-13/safety-pricing.md for uncertainty and live observation limits.
"""

import math
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Literal

from inventory_tracking.combat import threats
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.policy import Point, clear_line
from inventory_tracking.combat.sim import casters as rules
from inventory_tracking.combat.sim.guard import BOSSES, UNIQUE_FLAG, UNIQUE_STUN, GuardRule
from inventory_tracking.combat.sim.monsters import GAME_RATE, SHOT_REACH, Traits, shooter_of, shoots, swing_of
from inventory_tracking.combat.survival import Pressure, Supply
from inventory_tracking.config import Config, Percent, Positive
from inventory_tracking.terror.danger import table as threat_table


Hands = Literal['battle', 'travel']
KINDS = ('physical', 'fire', 'lightning', 'cold', 'poison', 'magic')
# monstats deathDmg, verified in scenarios/threat/threat_table.json (2026-10-13).
# A corpse already struck by a projectile can explode before another look.
EXPLODING = frozenset((214, 215, 216, 441, 442, 443, 690, 691))
# The life price by fight (the player, 2026-10-13: "probably we need to have it for diablo, baal, nihlathak,
# mephisto, duriel"): monster classes (monstats.txt `*hcIdx`, pricing/raw/game-excel, the client's txt id; not
# the row's place among the data rows, one more past the expansion's divider row) whose presence makes a point of
# life dearer, each with its factor on `life_price`. Their own forms only, no minion: 211 duriel, 708 uberduriel;
# 242 mephisto, 704 ubermephisto; 243 diablo, 333 diabloclone, 705 uberdiablo; 526 nihlathakboss; 544 baalcrab
# (the throne's fight), 570 baalclone, 709 uberbaal. The factor: rca/2026-10-13/diablo.md "Hooked in" (the duel's
# sweep: x10 is where his lightning's median loss is 0 in the short and the long fight, for 9-10% more kill time).
DEAR_FACTOR = 10.0
DEAR = tuple((txt, DEAR_FACTOR) for txt in (211, 708, 242, 704, 243, 333, 705, 526, 544, 570, 709))


class SafetySettings(Config):
    floor: Percent = 65.0  # Q1/Q6: life is a hard constraint, potions are not borrowed life
    insist_floor: Percent = 40.0
    insist_per_second: Positive = 5.0
    # A level run (KP_1: "one press, then it runs the whole level") asks for its goal at every look as a held key
    # does: its blocked goal escalates by the same insistence (the veto stays). Off: only fresh presses insist.
    run_insists: bool = True
    horizon: Positive = 1.5
    veto_share: Percent = 5.0
    healing_seconds: Positive = 4.0  # Q6, seconds per potion
    rejuvenation_seconds: Positive = 20.0
    healing_points: Positive = 480.0  # named stand-in until the belt's potion quality is priced
    # (monster class, factor): while a hostile of the class is in the fight (alive, within the AI's awareness of
    # the character), a point of life costs `factor` times `life_price` (the dearest present). DEAR above.
    dear: tuple[tuple[int, float], ...] = DEAR
    commit_share: Positive = 0.20  # Q2, improvement required to leave a firing stand
    commit_seconds: Positive = 0.30
    fight_through: bool = True  # Q3: allow a strike to advance a pressed goal
    middle_detour: Positive = 6.0  # Q4; the middle leash itself belongs to steps 8-9
    recharge_notice: int = 20  # Q5; never an instruction to recharge
    press_enables_attack: bool = False  # Q7, intent remains the runner's
    middle_objects_need_press: bool = True  # Q8
    trials: int = 64
    # Seconds of the game's clock one look's pricing may take before it settles for the best found so far
    # (macros/safety.py: the plain retreat rays are left out after it); the decision cadence is 0.12 s.
    look_seconds: Positive = 0.08
    # I2, no attack pause: with attack mode on and a hostile in reach, a move or a use is not made when the seconds
    # since the last strike and the act's own would pass this, while a strike here fits the budget (the strike
    # first, the act at the next look). The requirement is 2 s; the rest is the next look and the cast's start.
    strike_gap: Positive = 1.6
    seed: int = 61013  # same facts, same samples, independent of process hash/random state
    companion_uncertainty: float = 0.15  # nearest wins; companion motion is unobserved over the dwell
    unknown_damage_factor: Positive = 3.0  # an unread boss AI (Diablo): table blow, conservative burst factor
    unknown_period: Positive = 1.0
    unknown_points: Positive = 500.0  # no table row: up to 1500 after the conservative burst factor
    # An unread AI of an ordinary type is priced by the simulator's own fit on the takes (combat/sim/monsters.py
    # `swing_of`, `shooter_of`: swings and shots a second, the share that takes life, the fit's upper bound where it
    # has one) times this margin. Second pass, 2026-10-13: the factor-3 table stand-in priced the River of Flame's
    # Abyss Knights at 200+ points per 0.72 s each while the take lost no life in 106 s (safety-pricing.md).
    fitted_margin: Positive = 2.0
    # The character's own strikes (combat/stance.py `falls`, cast after cast at CAST_SECONDS): each rollout draws
    # how much later than forecast the hostiles die, one factor for all of them, from these quantiles at even
    # steps (the least, the deciles, the most), or never with `strike_never` percent. Measured in the arena
    # (second pass, 2026-10-13: 9,476 forecast deaths within 3 s at the looks that held, seal-pack, vizier-seal,
    # four-packs; median 1.78; 7.5% never died while the character stayed): the build's engine, not the game.
    strike_spread: tuple[float, ...] = (0.2, 0.43, 0.78, 1.06, 1.38, 1.78, 2.33, 3.13, 4.67, 8.37, 20.0)
    strike_never: Percent = 7.5
    # A guard the build keeps (macros/build.py `Shield`), shown up at the look: the share of its pool taken to be
    # left. The client is not told of the pool's fall (rca/2026-10-13/sim-casters.md section 9): a stand-in.
    guard_left: Percent = 50.0
    corpse_radius: Positive = 5.0
    move_overhead: Positive = 0.5
    hold_dwell: Positive = 0.72
    landing_dwell: Positive = 0.36  # following decision and residual cast delay, separate from transit
    operate_dwell: Positive = 1.5  # the hands' time limit at an object or a drop (macros/hunt.py `priced_for`)
    # Seconds at an object after the walk to it until its use takes: the exposure of the act (second pass: in the
    # arena a seal 10 units off opened 0.9 to 1.3 s after the decision, the walk included).
    use_dwell: Positive = 0.5


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
    # The client's mode (monmode.txt) and the frames since the look first saw it in that mode: a read model
    # (combat/threats) prices what an act under way still brings.
    mode: int = 0
    mode_frames: int = 0


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
    # What one look has priced already (`exposure` by hostiles, place, dwell and protection): the candidates of a
    # look share places and dwells, and a projected look (`approach`) shares this memo under its own hostiles.
    memo: dict = field(default_factory=dict, compare=False, repr=False)
    # Missiles in flight of the classes the read models ask for (combat/threats `missiles`): (owner unit, where,
    # heading in radians, and its class when the look read it: macros/safety.py `in_flight`).
    missiles: tuple[tuple[int, Point, float] | tuple[int, Point, float, int], ...] = ()
    # A draw priced on the look (`sent_onto`): the hostiles it turns to the companions where they now stand, and
    # where the companions stood before it, which every other hostile still weighs (`bodies`). None: no draw.
    drawn: frozenset[int] | None = None
    stood: tuple[Point, ...] = ()
    # What lies on the ground and harms where it lies, by its read model (combat/threats `Lingering`): priced over a
    # way whether or not its caster is still about (Diablo's fire wall after his death).
    ground: tuple[tuple[threats.Lingering, tuple[threats.Lying, ...]], ...] = ()


def bodies(seen: Look, m: Hostile) -> tuple[Point, ...]:
    """The companions' places a hostile weighs for whom it goes for (the nearest body): where they stand, or, for a
    hostile a draw did not turn (`sent_onto`'s `pack`), where they stood before it."""
    if seen.drawn is None or m.unit in seen.drawn:
        return seen.companions
    return seen.stood


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
    # Seconds into the dwell its blows begin and end (the approach first): a death in between ends them.
    begins: float = 0.0
    ends: float = 0.0
    # Blows' worth of time a landed blow stuns its striker for while the guard stands (0: never stunned), and
    # the chance a landing stuns at all (a unique's 10%).
    stun: float = 0.0
    stuns: float = 1.0


@lru_cache(maxsize=4096)
def traits(txt: int, level: int | None, flags: int, mods: tuple[int, ...], tier: int) -> Traits:
    return Traits.of(txt, level, flags, mods, tier)


def exposure(
    seen: Look,
    place: Point,
    dwell: float,
    protection: Protection,
    settings: SafetySettings,
    alive: Mapping[int, float] | None = None,
):
    """A*w*n*hit*points, retaining each burst as one event (flames correlate). `alive`: seconds into the
    dwell a hostile still lives (the character's own strikes, combat/stance.py `falls`); absent: all of it."""
    key = (seen.hostiles, seen.companions, seen.drawn, seen.stood, place, dwell, protection, settings)
    key = key if alive is None else None
    if key is not None:
        known = seen.memo.get(key)
        if known is not None:
            return known
    found: list[Exposure] = []
    unknown: list[int] = []
    curses = 0.0
    for m in sorted(seen.hostiles, key=lambda m: m.unit):
        lives = dwell if alive is None else min(dwell, alive.get(m.unit, math.inf))
        if lives <= 0:
            continue
        events, curse_rate, stand_ins = hostile_exposure(m, seen, place, lives, protection, settings)
        found.extend(events)
        curses += curse_rate
        unknown.extend(stand_ins)
    priced = tuple(e for e in found if e.blows > 0 and e.chance > 0), 1 - math.exp(-curses), tuple(sorted(set(unknown)))
    if key is not None:
        seen.memo[key] = priced
    return priced


def hostile_exposure(
    m: Hostile, seen: Look, place: Point, dwell: float, protection: Protection, settings: SafetySettings
):
    """One hostile's AI branches, evaluated immediately against one immutable look."""
    found: list[Exposure] = []
    unknown: list[int] = []
    curses = 0.0
    d = rules.ai_distance(m.at, place)
    near = min((rules.ai_distance(m.at, p) for p in bodies(seen, m)), default=math.inf)
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
        stun = stuns = 0.0
        guard = protection.guard
        if guard is not None and guard.stun > 0 and m.txt not in BOSSES and speed > 0:
            # The guard's stun (combat/sim/guard.py): the striker stands its frames out after a landed blow.
            stun, stuns = guard.stun / GAME_RATE / period, UNIQUE_STUN if m.flags & UNIQUE_FLAG else 1.0
        found.append(
            Exposure(
                m.unit, melee_time / period * chance, share * hit * (1 - protection.block), tuple(parts), True,
                dwell - melee_time, dwell, stun, stuns,
            )
        )  # fmt: skip

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
        found.append(Exposure(m.unit, active / period * chance, share, tuple(parts), False, dwell - active, dwell))

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
            found[-1] = replace(found[-1], parts=found[-1].parts + extra)
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
    elif threats.of(m.txt) is not None:
        # A read model (combat/threats) prices its acts over the whole path (`threat_exposure`); its melee is
        # not in the model: the conservative table stand-in, as for an unread boss.
        unknown.append(m.txt)
        swing()
    elif m.txt in BOSSES or str(m.txt) not in tables()['monsters']:
        # A boss whose AI is not read (Diablo), or a type with no monstats row: the conservative table stand-in,
        # not a claim to know it.
        unknown.append(m.txt)
        threat = threat_table().monsters.get(m.txt)
        if shoots(m.txt) or (threat is not None and threat.ranged):
            points = max(model.damage[1], 100.0) * settings.unknown_damage_factor
            kind = min(KINDS, key=lambda k: dict(protection.resists).get(k, 0.0))
            shot = ((kind, points / 2, points),)
            found.append(Exposure(m.unit, t / settings.unknown_period, share, shot, False, dwell - t, dwell))
        else:
            swing()
    else:
        # An ordinary type whose AI is not read: the simulator's fit on the takes (what the arena plays for it),
        # times `fitted_margin`. The fit's chance to take life has the ward and the resistances in it already.
        unknown.append(m.txt)
        threat = threat_table().monsters.get(m.txt)
        margin = settings.fitted_margin
        if shoots(m.txt) or (threat is not None and threat.ranged):
            fit = shooter_of(m.txt)
            points = max(model.damage[1], fit['takes_life'].get('mean_hit', 0.0), 1.0)
            kind = min(KINDS, key=lambda k: dict(protection.resists).get(k, 0.0))
            chance = min(1.0, fit['takes_life']['value'] * margin) * fit['aim']['value']
            if d <= SHOT_REACH:
                found.append(
                    Exposure(
                        m.unit, t * fit['rate']['value'], chance, ((kind, points / 2, points),), False, dwell - t, dwell
                    )
                )
        else:
            fit = swing_of(m.txt)
            takes = fit['takes_life']
            chance = min(1.0, takes.get('high', takes['value']) * margin)
            parts = [('physical', *model.damage)] if model.damage[1] > 0 else [('physical', 0.0, 100.0)]
            parts += [(k, model.damage[0] * lo, model.damage[1] * hi) for k, lo, hi in model.elements]
            found.append(
                Exposure(
                    m.unit, melee_time * fit['rate']['value'], share * chance, tuple(parts), True, dwell - melee_time,
                    dwell,
                )
            )  # fmt: skip
    return tuple(found), curses, tuple(unknown)


def threat_exposure(
    seen: Look, path: tuple[tuple[Point, float, Hands], ...], protection: Protection, settings: SafetySettings
) -> tuple[Exposure, ...]:
    """The acts of hostiles with a read model (combat/threats), priced over the whole path at once: an act under
    way (a stream aimed at where the character is at each frame) is not a rate at a place, so the path is not cut
    into places for it. Their begins and ends are seconds of the path. Each part is one correlated event."""
    found: list[Exposure] = []
    legs = spanned(path, settings)
    start, end = legs[0][0], legs[-1][0]
    for m in seen.hostiles:
        model = threats.of(m.txt)
        if model is None:
            continue
        d = rules.ai_distance(m.at, start)
        near = min((rules.ai_distance(m.at, p) for p in bodies(seen, m)), default=math.inf)
        if min(d, near) >= rules.RADIUS:
            continue
        flying, kinds = threats.flying_of(seen.missiles, m.unit)
        acting = threats.Acting(m.at, m.mode, m.mode_frames, flying, kinds)
        key = ('threat', m, flying, kinds, legs, protection.resists, len(seen.companions))
        parts = seen.memo.get(key)
        if parts is None:
            parts = seen.memo[key] = model.exposure(
                acting,
                legs,
                seen=clear_line(seen.blocked, m.at, end),
                companions=len(seen.companions),
                resists=dict(protection.resists) or None,
            )
        for part in parts:
            points = tuple((kind, value, value) for kind, value in part.points)
            found.append(Exposure(m.unit, part.casts, part.chance, points, False, part.begins, part.ends))
    return tuple(e for e in found if e.blows > 0 and e.chance > 0)


def spanned(path: tuple[tuple[Point, float, Hands], ...], settings: SafetySettings) -> threats.Legs:
    """The path as a read model's legs, over the span every candidate of a look is priced over (`horizon`, standing
    at its end after it): an act under way lands later than a short hold looks, and a step's own path is longer than
    a hold's. Over their own spans the step would carry missiles the hold leaves to the next look."""
    legs = tuple((place, max(0.0, dwell)) for place, dwell, _ in path)
    spent = sum(dwell for _, dwell in legs)
    if spent < settings.horizon:
        legs += ((legs[-1][0], settings.horizon - spent),)
    return legs


GROUND_UNIT = -1  # the contributor the harm of what lies on the ground is told under (`Harm.by`): no monster's unit


def ground_exposure(
    seen: Look, path: tuple[tuple[Point, float, Hands], ...], settings: SafetySettings
) -> tuple[Exposure, ...]:
    """What lies on the ground (`Look.ground`, combat/threats `Lingering`) over the whole path at once, as
    `threat_exposure` prices an act under way: a flame harms the frames the way is in it, its caster alive or not."""
    if not seen.ground:
        return ()
    legs = spanned(path, settings)
    found: list[Exposure] = []
    for model, lying in seen.ground:
        key = ('ground', model, lying, legs)
        parts = seen.memo.get(key)
        if parts is None:
            parts = seen.memo[key] = model.exposure(lying, legs)
        for part in parts:
            points = tuple((kind, value, value) for kind, value in part.points)
            found.append(Exposure(GROUND_UNIT, part.casts, part.chance, points, False, part.begins, part.ends))
    return tuple(e for e in found if e.blows > 0 and e.chance > 0)


def life_factor(seen: Look, place: Point, settings: SafetySettings) -> float:
    """The factor on the price of life while the fight has a hostile of a dear class (`SafetySettings.dear`)
    within the AI's awareness of `place` (the dearest of them); 1 otherwise."""
    dear = dict(settings.dear)
    return max(
        (dear[m.txt] for m in seen.hostiles if m.txt in dear and rules.ai_distance(m.at, place) < rules.RADIUS),
        default=1.0,
    )


def approach(seen: Look, place: Point, elapsed: float) -> Look:
    """Project pursuit during a leg; actors do not freeze while weapons are swapped.

    Nearest target and table walking speed are known. A melee approach is the
    conservative branch for mixed melee/casting AIs; ranged AIs stop at cast range.
    Walls stop this straight local projection. No unseen actor is invented.
    """
    moved = []
    for m in seen.hostiles:
        target = min((place, *bodies(seen, m)), key=lambda p: rules.ai_distance(m.at, p))
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


def sent_onto(
    seen: Look, sent: tuple[int, ...], target: Point, reach: float, beside: float, pack: float = math.inf
) -> Look:
    """The look with the companions at `sent` (indices into `companions`) that stand within `reach` of `target`
    put `beside` units from it, each on its own side of it (straight from the target where one stood on it): a
    cast that sends them onto one hostile (macros/build.py `Draw`). The hostiles within `pack` units of the target
    weigh them where they land, the nearest body by `share` (the client's rule): the target and what stands round
    it turn to them; every other hostile weighs them where they stood (`bodies`; the build's `Draw.pack`, measured:
    rca/2026-10-14/death-mark-engage.md §4)."""
    moved = list(seen.companions)
    for index in sent:
        if index >= len(moved):
            continue
        at = moved[index]
        gap = math.dist(at, target)
        if gap > reach:
            continue
        dx, dy = ((at[0] - target[0]) / gap, (at[1] - target[1]) / gap) if gap > 1e-6 else (1.0, 0.0)
        moved[index] = (target[0] + dx * beside, target[1] + dy * beside)
    turned = frozenset(m.unit for m in seen.hostiles if math.dist(m.at, target) <= pack)
    stood = seen.companions if seen.drawn is None else seen.stood
    return replace(seen, companions=tuple(moved), drawn=turned, stood=stood)


def harm(
    seen: Look,
    place: Point,
    dwell: float,
    hands: Hands,
    settings: SafetySettings | None = None,
    deaths: Mapping[int, float] | None = None,
) -> Harm:
    return harm_path(seen, ((place, dwell, hands),), settings, deaths)


def harm_path(
    seen: Look,
    path: tuple[tuple[Point, float, Hands], ...],
    settings: SafetySettings | None = None,
    deaths: Mapping[int, float] | None = None,
) -> Harm:
    """One event clock over a trajectory; only its final stand is tactically barred.

    Splitting a walk into integration slices must not restart a hostile's burst
    on every slice. The fractional attack phase carries across places and hands.
    `deaths`: seconds from the path's start at which a hostile dies by the
    character's own strikes as forecast (combat/stance.py `falls`); each
    rollout draws how much later they come (`strike_spread`, `strike_never`)
    and a hostile deals nothing after its death. Absent: no outgoing damage.
    """
    settings = settings or SafetySettings()
    if not path:
        return Harm()
    phases = []
    unknown = set()
    uncursed = 1.0
    elapsed = 0.0
    last = seen.battle if path[-1][2] == 'battle' else seen.travel
    acting = threat_exposure(seen, path, last, settings) + ground_exposure(seen, path, settings)
    if acting:
        phases.append((acting, last, 0.0))
    for index, (place, dwell, hands) in enumerate(path):
        protection = seen.battle if hands == 'battle' else seen.travel
        events, cursed, stand_ins = exposure(seen, place, max(0.0, dwell), protection, settings)
        phases.append((events, protection, elapsed))
        uncursed *= 1 - cursed
        unknown.update(stand_ins)
        elapsed += max(0.0, dwell)
        if index + 1 < len(path):
            seen = approach(seen, place, dwell)
    place, dwell, _ = path[-1]
    barred = 'a tactic bars this place' if seen.barred is not None and seen.barred(place) else None
    if dwell > 0 and any(m.txt in EXPLODING and math.dist(m.at, place) < settings.corpse_radius for m in seen.hostiles):
        barred = 'an exploding corpse can reach this place'
    if not any(events for events, _, _ in phases):
        return Harm(barred=barred, stand_ins=tuple(sorted(unknown)))
    rng = random.Random(settings.seed)
    losses: list[float] = []
    totals: dict[int, float] = {}
    # A curse is shared by all blows in a rollout. No healing promised in advance.
    spread = settings.strike_spread
    for _ in range(settings.trials):
        curse = rng.randrange(3) if rng.random() < 1 - uncursed else -1
        late = math.inf
        if deaths:
            # How much later than forecast the strikes kill in this rollout, one factor for all (misses, moves).
            roll = rng.random()
            if roll >= settings.strike_never / 100:
                place_ = roll * (len(spread) - 1)
                low = min(int(place_), len(spread) - 2)
                late = spread[low] + (spread[low + 1] - spread[low]) * (place_ - low)
        pool = phases[0][1].pool
        clocks: dict[tuple, float] = {}
        loss = 0.0
        for events, protection, start in phases:
            resists, flat, absorb = dict(protection.resists), dict(protection.flat), dict(protection.absorb)
            for event in events:
                key = (event.unit, event.parts, event.melee)
                if key not in clocks:
                    clocks[key] = rng.random()
                # The blows fall where the event's phase crosses a whole number; a stun sets it back.
                phase, remaining = clocks[key], event.blows
                death = deaths.get(event.unit) if deaths else None
                if death is not None and event.ends > event.begins:
                    # Its blows are spread over [begins, ends] of the dwell; none after the rollout's death.
                    lived = min(event.ends, death * late - start) - event.begins
                    remaining *= min(1.0, max(0.0, lived / (event.ends - event.begins)))
                while True:
                    ahead = math.floor(phase) + 1 - phase
                    if ahead > remaining:
                        phase += remaining
                        break
                    remaining -= ahead
                    phase = math.floor(phase) + 1
                    if rng.random() >= event.chance:
                        continue
                    points = 0.0
                    guarded = pool > 0
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
                    # Not for the blow that took the pool to 0 (combat/sim/guard.py).
                    if event.stun and guarded and pool > 0 and (event.stuns >= 1 or rng.random() < event.stuns):
                        phase -= event.stun
                clocks[key] = phase
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


def budget(
    life: float,
    most: float,
    pressure: Pressure,
    settings: SafetySettings,
    *,
    insisting: float = 0.0,
    spendable: float | None = None,
) -> float:
    """The life a look may put at risk over the horizon: what is above the floor (`stock_floor`, the belt counted),
    less the share the pressure takes over the horizon. Insisting on a blocked goal lowers the floor as before."""
    floor = stock_floor(most, settings, spendable)
    floor = max(settings.insist_floor, floor - max(0.0, insisting) * settings.insist_per_second)
    return max(0.0, life - floor / 100 * most) * (1 - min(1.0, pressure.rate * settings.horizon))


def stock_floor(most: float, settings: SafetySettings, spendable: float | None) -> float:
    """The life floor with the belt counted (the player, 2026-10-14: "the life budget scales with the potion stock";
    rca/2026-10-14/run-1932-findings.md issue 2: the budget was 636 with 8 of 8 healing potions and with 2 of 8, and
    the character warped into 21 hostiles with 2). The life a look spends is life the belt has to give back after it:
    `spendable` is what its healing potions beyond the ones kept for under the floor give back, each worth
    `healing_points` (macros/supply.py `spendable`). A point lost is spendable only while the belt can buy it back,
    so the floor is where full life less what the belt gives back leaves the character, never under `floor`: with a
    stocked belt it is `floor` (8 of 8 at 1818 life: the potions give 2880 back, full life less that is far under
    65%); with 3 of 8 (one beyond the 2 kept) it is 74% (480 back); with the kept ones alone it is full life, and
    only an insisted goal lowers it (`budget`). None: the belt not counted (unread), the floor as it was."""
    if spendable is None or most <= 0:
        return settings.floor
    return min(100.0, max(settings.floor, 100.0 * (1.0 - spendable / most)))


def life_price(supply: Supply, most: float, settings: SafetySettings) -> float:
    if supply.healing:
        return settings.healing_seconds / settings.healing_points
    return settings.rejuvenation_seconds / max(most, 1.0)
