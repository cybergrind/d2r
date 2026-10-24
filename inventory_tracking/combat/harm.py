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
from itertools import pairwise
from typing import Literal

from inventory_tracking.combat import bolts, threats
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.policy import Point, clear_line
from inventory_tracking.combat.sim import casters as rules
from inventory_tracking.combat.sim.guard import BOSSES, UNIQUE_FLAG, UNIQUE_STUN, GuardRule
from inventory_tracking.combat.sim.monsters import GAME_RATE, SHOT_REACH, Traits, shooter_of, shoots, swing_of
from inventory_tracking.combat.survival import Pressure, Supply
from inventory_tracking.combat.threats import dolls
from inventory_tracking.config import Config, Percent, Positive
from inventory_tracking.terror.danger import table as threat_table


Hands = Literal['battle', 'travel']
KINDS = ('physical', 'fire', 'lightning', 'cold', 'poison', 'magic')
# monstats deathDmg (F0, 2026-10-21: built from the game's table, combat/threats/dolls.py `exploding`; before, a list of
# 8 that left out 212, 213, 444, the siege windows and the Baal clone; rca/2026-10-21/dolls-tz-findings.md §2).
# A corpse already struck by a projectile can explode before another look.
EXPLODING = dolls.exploding()
# Monster classes (monstats.txt `*hcIdx`, the client's txt id) whose presence makes life dearer by DEAR_FACTOR: the
# bosses' own forms, no minion (the player, 2026-10-13: "probably we need to have it for diablo, baal, nihlathak,
# mephisto, duriel"). The factor: rca/2026-10-13/diablo.md "Hooked in".
DEAR_FACTOR = 10.0
DEAR = tuple((txt, DEAR_FACTOR) for txt in (211, 708, 242, 704, 243, 333, 705, 526, 544, 570, 709))
# The share of the life budget a look keeps by the healing potions the belt can spend (macros/supply.py `spendable`):
# (potions beyond, share) points, linear between, flat past the ends (the player, 2026-10-15: "keep the full budget
# down to 4 potions, never below about half"; rca/2026-10-14/run-1932-findings.md "Arena").
STOCK_SHARE = ((0.0, 0.5), (2.0, 1.0))


class SafetySettings(Config):
    floor: Percent = 65.0  # Q1/Q6: life is a hard constraint, potions are not borrowed life
    insist_floor: Percent = 40.0
    insist_per_second: Positive = 5.0
    # A level run (KP_1) insists on its blocked goal at every look as a held key does (the veto stays).
    run_insists: bool = True
    horizon: Positive = 1.5
    veto_share: Percent = 5.0
    healing_seconds: Positive = 4.0  # Q6, seconds per potion
    rejuvenation_seconds: Positive = 20.0
    healing_points: Positive = 480.0  # named stand-in until the belt's potion quality is priced
    # (monster class, factor): while one is in the fight, life costs `factor` x `life_price` (the dearest present).
    dear: tuple[tuple[int, float], ...] = DEAR
    stock_share: tuple[tuple[float, float], ...] = STOCK_SHARE  # (potions beyond the kept, budget share): STOCK_SHARE
    commit_share: Positive = 0.20  # Q2, improvement required to leave a firing stand
    commit_seconds: Positive = 0.30
    fight_through: bool = True  # Q3: allow a strike to advance a pressed goal
    middle_detour: Positive = 6.0  # Q4; the middle leash itself belongs to steps 8-9
    recharge_notice: int = 20  # Q5; never an instruction to recharge
    press_enables_attack: bool = False  # Q7, intent remains the runner's
    middle_objects_need_press: bool = True  # Q8
    trials: int = 64
    # Seconds one look's pricing may take before it settles for the best so far (decision cadence 0.12 s).
    look_seconds: Positive = 0.08
    # I2, no attack pause (2 s required): with a hostile in reach, a move or use that would leave this long since the
    # last strike waits for a strike first, if one fits the budget.
    strike_gap: Positive = 1.6
    seed: int = 61013  # same facts, same samples, independent of process hash/random state
    companion_uncertainty: float = 0.15  # nearest wins; companion motion is unobserved over the dwell
    unknown_damage_factor: Positive = 3.0  # an unread boss AI (Diablo): table blow, conservative burst factor
    unknown_period: Positive = 1.0
    unknown_points: Positive = 500.0  # no table row: up to 1500 after the conservative burst factor
    # An unread AI of an ordinary type: the simulator's fit (combat/sim/monsters.py `swing_of`, `shooter_of`) times
    # this margin (the table stand-in overpriced Abyss Knights, rca/2026-10-13/safety-pricing.md).
    fitted_margin: Positive = 2.0
    # How much later than forecast (combat/stance.py `falls`) the hostiles die, one factor a rollout drawn from these
    # quantiles (least, deciles, most), or never with `strike_never` percent. Measured in the arena (2026-10-13).
    strike_spread: tuple[float, ...] = (0.2, 0.43, 0.78, 1.06, 1.38, 1.78, 2.33, 3.13, 4.67, 8.37, 20.0)
    strike_never: Percent = 7.5
    # The share of a standing guard's pool taken to be left: the client does not show it (sim-casters.md section 9).
    guard_left: Percent = 50.0
    corpse_radius: Positive = 5.0
    move_overhead: Positive = 0.5
    hold_dwell: Positive = 0.72
    landing_dwell: Positive = 0.36  # following decision and residual cast delay, separate from transit
    operate_dwell: Positive = 1.5  # the hands' time limit at an object or a drop (macros/hunting/moves.py `priced_for`)
    # Seconds at an object after the walk to it until its use takes.
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
    # The factor the auras round it put on its blows' physical points (Might, Concentration, Fanaticism: +% damage,
    # which is physical; macros/safety.py AURA_FORECAST builds it from the Aura Enchanted hostiles about); 1: none
    raised: float = 1.0
    # Units a second it was seen to move at (macros/safety.py OBSERVED_SPEED); 0: not seen moving, its table
    # walk (`kind_of`) alone. Its walk is the larger
    speed: float = 0.0
    # The share of the conservative stand-in's blows (an unread boss's, `stood_in`) the fight's evidence leaves
    # (macros/safety.py STAND_IN_EVIDENCE: seconds within its radius and the life lost there); 1: the stand-in whole
    tempered: float = 1.0
    # Throws a second it makes at the character as the look read them (combat/bolts.py READ_THROWS, macros/safety.py
    # `Safety.throws_read`): an unread type is priced by them, not by the pooled fit; 0: none read
    throws: float = 0.0


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
    # A draw priced on the look (`sent_onto`): the hostiles it turns to the companions; None: no draw.
    drawn: frozenset[int] | None = None
    stood: tuple[Point, ...] = ()
    # What lies on the ground and harms where it lies, by its read model (combat/threats `Lingering`): priced over a
    # way whether or not its caster is still about (Diablo's fire wall after his death).
    ground: tuple[tuple[threats.Lingering, tuple[threats.Lying, ...]], ...] = ()
    # The live companions' places (not dying, not dead): a throw at the character meets the first one on its line
    # (combat/bolts.py READ_THROWS, `bolts.covered`)
    cover: tuple[Point, ...] = ()


# The player, 2026-10-21 ~20:34, on the second tier 5 Herald of the Arachnid Lair (20:31:17-24, take
# 20261021T172936Z-84): "we had a quite bad positioning and suffered alot of damage and wasn't able to reposition".
# The merc and the demons stood 0-0.6 from the character (a Teleport takes the allies within 10 along,
# rca/2026-10-21/herald-gloam-findings.md §3), so each Flame Spider in melee was priced at `companion_uncertainty`
# (the nearest body wins) though 58% of them stood nearer an ally: the take lost 388 life a spider-second within 4,
# the hold was priced at 133 over 10 s and every Teleport out at 1033 (rca/2026-10-21/arachnid-herald-2-findings.md).
# True: a companion within GLUED of the priced place stands with the character and takes no blow off it. False: the
# nearest body wins, however near the character it stands.
GLUED_SHARE = False
# AURA_SWINGERS (2026-10-22, the coordinator from the sim's round 4: "weigh the aura on units actually swinging at
# us"): the auras' raise (`Hostile.raised`, macros/safety.py AURA_FORECAST) goes on the blows of a hostile nearer the
# character than any companion (the body it goes for, `hostile_exposure`), not on one nearer the demons. False: on
# every hostile's blows, as before. `most_blow` (macros/safety.py REACH_BAR) keeps the raise whatever. Off (2026-10-22,
# measured): the capped t5 Hulk Herald stayed at 7 of 20 dead and fane-death-20 died 3 times in 40 plays.
AURA_SWINGERS = False
# NEAR_WAKES (2026-10-22, the sim's pursuit-mode fane-death-20, seed 7, on-time looks: the pursuit's Teleport landed
# beside the x5.75 unique Night Lord idle in mode 1 with no line to the landing, priced at nothing; it woke and one
# blow of 2968 killed from 86%. The coordinator: "a hostile within reach of the landing counts by its raised top blow
# whatever its mode. Only far, inactive hostiles should price at 0"). True: a neutral hostile with no line to the place
# is priced as any other when it can walk to the place's reach within WAKE_SECONDS. False: priced at nothing, as
# before.
NEAR_WAKES = True
WAKE_SECONDS = 1.0
# CURSED_PRICED (2026-10-24, the mana-burn agent's find on the Halls of the Dead death of 2026-10-23, take
# 20261023T202950Z-57: Amplify Damage, state 9, came on the whole party at 23:30:27.4, the physical resistance 18 to
# -82, from the unique Hollow One 1316109150 and its Returned, monumod 7 'curse' ("Cursed"; minions inherit it), 5.8 to
# 12.7 off; rca/2026-10-24/cast-hold-findings.md §4): a Cursed hostile curses the party from afar, and only a curse
# already on the character was priced (its resistances as read), so a Cursed pack's coming blows were priced at the
# uncursed physical share, under half the cursed one. The takes of 2026-10-23..24 (21 onsets of state 9 on the
# character, 13 with a Cursed hostile about): its nearest Cursed 3.5-18.7 off (median 12), 0.4-6.8 s (median 1.1) after
# it came within 20. True: each Cursed hostile within CURSED_REACH of a priced place puts Amplify Damage on a rollout
# at a rate of one in CURSED_SECONDS of the dwell there (`rollouts`: the physical blows at Amplify Damage's share, as
# OBLIVION_KNIGHT's curse); with it already read on the character the share is floored at -100 (an extra curse adds at
# most 1.82 -> 2.0). False: as before. On 2026-10-24 ~14:40 as a speed change, not a survival fix: 800 GLUED pairs
# with 0 new deaths, fane Heralds killed 18 -> 24, pursuit 28 -> 31; the halls_curse cut does not die with it off.
CURSED_PRICED = True
CURSED = 7  # monumod.txt 'curse' ("Cursed"), as hostiles' `modifiers` hold it
CURSED_REACH = 15.0
CURSED_SECONDS = 1.0
GLUED = 3.0  # units: combat/pack.py DEMON_APART, the demon that "stands with" the character
# STAND_IN_TEMPER (2026-10-22, Sewers Level 3, 23:15:49-23:20:30, take 20261022T201417Z-49; rca/2026-10-22/
# walled-boss-findings.md §2): Radament (monstats 229, a boss with no read AI) priced by the conservative stand-in, a
# shot of three times his table blow every second anywhere within RADIUS, about 1977 life in 1.5 s from 5 or from 30
# units, so every act toward him was vetoed for 4.5 minutes in which the character lost no life at all; struck from 21
# units at last, he died in 13 s. True: the stand-in's rate and its burst over the table blow are scaled by
# `Hostile.tempered`, what the fight has shown of the hostile (macros/safety.py STAND_IN_EVIDENCE): at the floor a blow
# a little over the table's, seldom; the one-blow bars (`most_blow`) are not. False: whole, as before
STAND_IN_TEMPER = True
# BOLTS_IN_FLIGHT (2026-10-23, Icy Cellar 04:35:48, take 20261023T013533Z-119; rca/2026-10-23/dominus-burst-findings):
# a tier 5 Herald pack of Dominus (succubus witches, no read AI) shot volleys of 3 bolts at a character standing 3.1 s;
# the hold was priced at 4 points while 7 bolts flew at it, and 4 took 1701 of 2943 in 0.17 s. True: the bolts of the
# families combat/bolts.py names, read in flight (macros/safety.py `Safety.look`), are each one blow where they reach
# the way (`bolt_exposure`); False: an unread shooter is its fitted rate alone, as before.
# On 2026-10-23 ~05:10: arena dominus-0535 lowest share min 0.06 -> 0.71, 660 danger/Fane/threat pairs unchanged
BOLTS_IN_FLIGHT = True


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


@lru_cache(maxsize=4096)
def kind_of(
    txt: int, level: int | None, flags: int, mods: tuple[int, ...], tier: int
) -> tuple[dict[str, str] | None, Traits, str | None, float, float]:
    """A hostile's type and roll as the tables price them: its monstats row, its traits, the read AI it thinks by,
    its walk (units a second) and its AI delay (frames)."""
    row = rules.row_of(txt)
    model = traits(txt, level, flags, mods, tier)
    speed = rules.speed_of(row) * 25 if row else model.speed * 25
    delay = rules.number(row, 'aidel(H)', 15) if row else 13
    return row, model, rules.mind_of(txt), speed, delay


@lru_cache(maxsize=4096)
def hit_of(txt: int, level: int, defence: float, against: int) -> float:
    row = rules.row_of(txt)
    assert row is not None
    return rules.hit_chance(row, level, defence, against)


@lru_cache(maxsize=4096)
def missile_terms(mid: int, txt: int, slot: int) -> tuple[float, tuple[tuple[str, float, float, float], ...]]:
    """A caster's missile as the tables give it: how far it flies, and its damage by kind at the caster's skill
    level as (kind, least, most, length)."""
    mr = rules.missile_row(mid)
    row = rules.row_of(txt)
    assert row is not None
    level = rules.skill_level(row, slot)
    damage = []
    for k, (lo, hi) in rules.missile_damage(mid, level).items():
        # Reserve the full poison duration at impact. This deliberately
        # overprices damage after the look, but does not forget it when a
        # trajectory is split or an afflicted character leaves missile range.
        length = rules.number(mr, 'ELen') if k == 'poison' else 1.0
        damage.append((k, lo, hi, length))
    return rules.missile_step(mid) * rules.number(mr, 'Range') + rules.CONTACT, tuple(damage)


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


def sighted(seen: Look, start: Point, end: Point) -> bool:
    """`clear_line` over the look's walls, once a look: its walls do not change within it (the memo prices on that)."""
    if seen.blocked is None:
        return True
    key = ('line', seen.blocked, start, end)
    known = seen.memo.get(key)
    if known is None:
        known = seen.memo[key] = clear_line(seen.blocked, start, end)
    return known


def wakes(m: Hostile, d: float) -> bool:
    """Whether a neutral hostile `d` off walks to the reach of the place within WAKE_SECONDS (NEAR_WAKES)."""
    return d <= rules.REACH + max(kind_of(m.txt, m.level, m.flags, m.modifiers, m.tier)[3], m.speed) * WAKE_SECONDS


def hostile_exposure(
    m: Hostile, seen: Look, place: Point, dwell: float, protection: Protection, settings: SafetySettings
):
    """One hostile's AI branches, evaluated immediately against one immutable look."""
    found: list[Exposure] = []
    unknown: list[int] = []
    curses = 0.0
    d = rules.ai_distance(m.at, place)
    near = min(
        (rules.ai_distance(m.at, p) for p in bodies(seen, m) if not (GLUED_SHARE and math.dist(p, place) < GLUED)),
        default=math.inf,
    )
    if min(d, near) >= rules.RADIUS:
        return (), 0.0, ()
    # Neutral and with no line: priced at nothing, unless it reaches the place within WAKE_SECONDS (NEAR_WAKES)
    if not m.active and not sighted(seen, m.at, place) and not (NEAR_WAKES and wakes(m, d)):
        return (), 0.0, ()
    share = 1.0 if d <= near else settings.companion_uncertainty
    # The auras round it on the blows of one that goes for the character (AURA_SWINGERS); one nearer a companion is
    # priced at its plain blow
    raised = m.raised if not AURA_SWINGERS or d <= near else 1.0
    t = max(0.0, dwell - m.stunned)
    if t <= 0:
        return (), 0.0, ()
    row, model, ai, speed, delay = kind_of(m.txt, m.level, m.flags, m.modifiers, m.tier)
    speed = max(speed, m.speed)  # as seen closing in (macros/safety.py OBSERVED_SPEED)
    # Reach during the dwell. A monster spends the approach time walking, not striking.
    melee_time = max(0.0, t - max(0.0, d - rules.REACH) / max(speed, 0.1))

    def swing(chance=1.0, burst: float | None = None):
        frames = rules.MODE_FRAMES.get((ai, 'A1'), 12) if ai else 12
        period = (frames + delay) / 25 if ai else settings.unknown_period
        hit = hit_of(m.txt, model.level, protection.defence, protection.level) if row else 0.95
        parts = [('physical', *model.damage)]
        if not ai and model.damage[1] <= 0:
            parts = [('physical', settings.unknown_points / 2, settings.unknown_points)]
        parts = [(k, lo * raised, hi * raised) if k == 'physical' else (k, lo, hi) for k, lo, hi in parts]
        parts += [(k, model.damage[0] * lo, model.damage[1] * hi) for k, lo, hi in model.elements]
        if not ai:
            factor = settings.unknown_damage_factor if burst is None else burst
            parts = [(k, lo * factor, hi * factor) for k, lo, hi in parts]
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
        flies, damage = missile_terms(mid, m.txt, slot)
        if distance > flies:
            return
        parts = [(k, lo * count * length, hi * count * length) for k, lo, hi, length in damage]
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
        temper = m.tempered if STAND_IN_TEMPER else 1.0  # what the fight has shown of it (STAND_IN_TEMPER)
        # Its rate and its burst over the table blow both by the share the evidence leaves: at none, one table blow
        burst = 1.0 + (settings.unknown_damage_factor - 1.0) * temper
        if shoots(m.txt) or (threat is not None and threat.ranged):
            points = max(model.damage[1], 100.0) * burst
            kind = min(KINDS, key=lambda k: dict(protection.resists).get(k, 0.0))
            shot = ((kind, points / 2, points),)
            found.append(Exposure(m.unit, t / settings.unknown_period * temper, share, shot, False, dwell - t, dwell))
        else:
            swing(temper, burst)
    else:
        # An ordinary type whose AI is not read: the simulator's fit on the takes (what the arena plays for it),
        # times `fitted_margin`. The fit's chance to take life has the ward and the resistances in it already.
        unknown.append(m.txt)
        threat = threat_table().monsters.get(m.txt)
        margin = settings.fitted_margin
        # Its throws as read (READ_THROWS) are priced over the whole path at once (`throw_exposure`), not the fit
        thrower = bolts.READ_THROWS and m.throws > 0
        if thrower and (shoots(m.txt) or (threat is not None and threat.ranged)):
            pass  # a shooter's read throws are its shots
        elif shoots(m.txt) or (threat is not None and threat.ranged):
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
            parts = [(k, lo * raised, hi * raised) for k, lo, hi in parts]  # the auras round it (`raised`)
            parts += [(k, model.damage[0] * lo, model.damage[1] * hi) for k, lo, hi in model.elements]
            found.append(
                Exposure(
                    m.unit, melee_time * fit['rate']['value'], share * chance, tuple(parts), True, dwell - melee_time,
                    dwell,
                )
            )  # fmt: skip
    return tuple(found), curses, tuple(unknown)


def unread(txt: int) -> bool:
    """Whether `hostile_exposure` prices type `txt` by a guess, not a reading of its acts: the simulator's fit of an
    ordinary type or the conservative stand-in of a boss (no read AI branch, no read model, combat/threats). Such a
    type's throws are read (combat/bolts.py READ_THROWS, macros/safety.py `Safety.throws_read`)."""
    if rules.mind_of(txt) in (rules.FINGER_MAGE, rules.DOOM_KNIGHT, rules.OBLIVION_KNIGHT, rules.MEGADEMON):
        return False
    return threats.of(txt) is None


def stood_in(txt: int) -> bool:
    """Whether `hostile_exposure` prices type `txt` by the conservative stand-in of a boss whose AI is not read (or a
    type with no monstats row): no read AI branch, no read model (STAND_IN_TEMPER)."""
    if rules.mind_of(txt) in (rules.FINGER_MAGE, rules.DOOM_KNIGHT, rules.OBLIVION_KNIGHT, rules.MEGADEMON):
        return False
    if threats.of(txt) is not None:
        return False
    return txt in BOSSES or str(txt) not in tables()['monsters']


def most_blow(m: Hostile, protection: Protection) -> tuple[float, float]:
    """(the most one melee blow of `m` takes, its walk in units a second): its table blow's most physical points times
    the auras round it (`Hostile.raised`) plus its elements' most, each after the resistances as read (the curses on
    the character in them), less the flat reduction. (0, its walk) for a type with no table blow."""
    _, model, _, speed, _ = kind_of(m.txt, m.level, m.flags, m.modifiers, m.tier)
    speed = max(speed, m.speed)  # as seen closing in (macros/safety.py OBSERVED_SPEED)
    most = model.damage[1]
    if most <= 0:
        return 0.0, speed
    flat = dict(protection.flat)
    parts = [('physical', most * m.raised), *((k, most * hi) for k, _, hi in model.elements)]
    taken = sum(
        max(0.0, points - flat.get(kind, 0.0)) * resisted(kind, protection.resists)[0] for kind, points in parts
    )
    return taken, speed


def threat_exposure(
    seen: Look, path: tuple[tuple[Point, float, Hands], ...], protection: Protection, settings: SafetySettings
) -> tuple[Exposure, ...]:
    """The acts of hostiles with a read model (combat/threats), priced over the whole path at once: an act under way
    is not a rate at a place. Each part is one correlated event."""
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
                seen=sighted(seen, m.at, end),
                companions=len(seen.companions),
                resists=dict(protection.resists) or None,
            )
        for part in parts:
            points = tuple((kind, value, value) for kind, value in part.points)
            found.append(Exposure(m.unit, part.casts, part.chance, points, False, part.begins, part.ends))
    return tuple(e for e in found if e.blows > 0 and e.chance > 0)


def spanned(path: tuple[tuple[Point, float, Hands], ...], settings: SafetySettings) -> threats.Legs:
    """The path as a read model's legs over the span every candidate of a look shares (`horizon`, standing at the
    end), so a step and a hold are priced over the same missiles."""
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


def bolt_exposure(
    seen: Look, path: tuple[tuple[Point, float, Hands], ...], settings: SafetySettings
) -> tuple[Exposure, ...]:
    """The bolts in flight of the shooters combat/bolts.py names (BOLTS_IN_FLIGHT), over the whole path at once: each
    that reaches the way where the way is then is one blow at that time (`bolts.hit_time`), landing with `bolts.LANDS`.
    A read model's own missiles are its own (`threat_exposure`). A bolt flies on after its shooter's death: the blow's
    `begins` is its `ends`, so no forecast death cuts it (`rollouts`)."""
    if not BOLTS_IN_FLIGHT or not seen.missiles:
        return ()
    owners = {m.unit: m for m in seen.hostiles if threats.of(m.txt) is None}
    legs = spanned(path, settings)
    found: list[Exposure] = []
    for missile in seen.missiles:
        if len(missile) < 4:
            continue
        owner, at, heading, kind = missile  # pyrefly: ignore[bad-unpacking]
        m = owners.get(owner)
        speed = bolts.speed_of(kind)
        if m is None or speed is None or kind not in bolts.classes_of(m.txt):
            continue
        key = ('bolt', at, heading, kind, legs)
        when = seen.memo.get(key, ())
        if when == ():
            when = seen.memo[key] = bolts.hit_time(at, heading, speed, legs)
        if when is None:
            continue
        parts = bolts.points(m.txt, m.level, m.flags, m.modifiers, m.tier, m.raised)
        lands = bolts.LANDS
        if bolts.READ_THROWS:
            # A companion on its way to where the way is then takes it first (READ_THROWS, `bolts.covered`)
            place = bolts.place_at(legs, when)
            lands *= bolts.covered(bolts.cover_at(seen.cover, legs[0][0], place), at, place)
        found.append(Exposure(m.unit, 1.0, lands, parts, False, when, when))
    return tuple(found)


def throw_exposure(seen: Look, path: tuple[tuple[Point, float, Hands], ...], protection: Protection) -> tuple:
    """The throws of the unread types whose rate at the character the look read (combat/bolts.py READ_THROWS,
    `Hostile.throws`), over the whole path at once: from when a throw let go now lands (its flight to the path's first
    place; the bolts in flight before it are `bolt_exposure`'s) and, out of SHOT_REACH, an awake one has walked into
    it, `throws` a second at each leg's place, each hitting by the game's rule (its A1 rating against the defence, then
    the block: 0.68 for the Hell Slingers of take 20261023T115109Z-46, which landed 0.6) unless a companion on its line
    takes it (`bolts.covered`), for its table blow raised by rank, tier and auras (`bolts.points`)."""
    if not bolts.READ_THROWS:
        return ()
    legs = tuple((place, max(0.0, dwell)) for place, dwell, _ in path)
    found: list[Exposure] = []
    for m in seen.hostiles:
        if m.throws <= 0 or not unread(m.txt):
            continue
        speeds = [speed for kind in bolts.classes_of(m.txt) if (speed := bolts.speed_of(kind)) is not None]
        parts = bolts.points(m.txt, m.level, m.flags, m.modifiers, m.tier, m.raised)
        if not speeds or not parts or rules.ai_distance(m.at, legs[0][0]) >= rules.RADIUS:
            continue
        walk = max(kind_of(m.txt, m.level, m.flags, m.modifiers, m.tier)[3], m.speed, 0.1)
        table = tables()['monsters'].get(str(m.txt))
        level = m.level or int(rules.number(table or {}, 'Level(H)', 1))
        hit = rules.hit_chance(table, level, protection.defence, protection.level) if table else rules.MOST_HIT / 100
        began = 0.0
        for place, dwell in legs:
            gap = math.dist(m.at, place)
            out = max(0.0, gap - SHOT_REACH)
            if out > 0 and not m.active:
                began += dwell
                continue
            first = m.stunned + out / walk + min(gap, SHOT_REACH) / min(speeds)
            begins, ends = max(began, first), began + dwell
            if ends > begins:
                cover = bolts.cover_at(seen.cover, legs[0][0], place)
                chance = hit * (1 - protection.block) * bolts.covered(cover, m.at, place)
                found.append(Exposure(m.unit, (ends - begins) * m.throws, chance, parts, False, begins, ends))
            began += dwell
    return tuple(found)


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
            if sighted(seen, m.at, point):
                m = replace(m, at=point)
        moved.append(m)
    return replace(seen, hostiles=tuple(moved))


def sent_onto(
    seen: Look, sent: tuple[int, ...], target: Point, reach: float, beside: float, pack: float = math.inf
) -> Look:
    """The look with the companions `sent` within `reach` of `target` put `beside` units from it, each on its own
    side (macros/build.py `Draw`). Hostiles within `pack` of the target weigh them where they land; others where
    they stood (`bodies`; rca/2026-10-14/death-mark-engage.md §4)."""
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


def amplify_rate(seen: Look, place: Point, dwell: float) -> float:
    """CURSED_PRICED: the rate of Amplify Damage the Cursed hostiles within CURSED_REACH of `place` put on a dwell of
    `dwell` s there (the curses expected)."""
    if not CURSED_PRICED or dwell <= 0:
        return 0.0
    near = sum(1 for m in seen.hostiles if CURSED in m.modifiers and math.dist(m.at, place) <= CURSED_REACH)
    return near * dwell / CURSED_SECONDS


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
    amplifying = 0.0  # CURSED_PRICED: the Cursed hostiles' Amplify Damage expected over the path (`amplify_rate`)
    elapsed = 0.0
    last = seen.battle if path[-1][2] == 'battle' else seen.travel
    acting = threat_exposure(seen, path, last, settings) + ground_exposure(seen, path, settings)
    acting += bolt_exposure(seen, path, settings) + throw_exposure(seen, path, last)
    if acting:
        phases.append((acting, last, 0.0))
    for index, (place, dwell, hands) in enumerate(path):
        protection = seen.battle if hands == 'battle' else seen.travel
        events, cursed, stand_ins = exposure(seen, place, max(0.0, dwell), protection, settings)
        phases.append((events, protection, elapsed))
        uncursed *= 1 - cursed
        amplifying += amplify_rate(seen, place, max(0.0, dwell))
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
    losses, totals = rollouts(phases, uncursed, settings, deaths, 1 - math.exp(-amplifying))
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


@lru_cache(maxsize=4096)
def resisted(kind: str, resistances: tuple[tuple[str, float], ...]) -> tuple[float, float, float, float]:
    """The factor a blow of `kind` keeps after the resistances (`Protection.resists`), by the rollout's curse + 1
    (none, Amplify Damage, Decrepify, Lower Resist)."""
    resists = dict(resistances)
    factors = []
    for curse in (-1, 0, 1, 2):
        delta = (
            (-100 if curse == 0 else -50 if curse == 1 else 0)
            if kind == 'physical'
            else (-55 if curse == 2 and kind not in ('magic',) else 0)
        )
        resistance = min(50.0 if kind == 'physical' else 75.0, max(-100.0, resists.get(kind, 0.0) + delta))
        factors.append(1 - resistance / 100)
    return factors[0], factors[1], factors[2], factors[3]


def rollouts(
    phases: list,
    uncursed: float,
    settings: SafetySettings,
    deaths: Mapping[int, float] | None,
    amplified: float = 0.0,
) -> tuple[list[float], dict[int, float]]:
    """The seeded rollouts of `harm_path`: each one's loss and the points by contributor over all of them.

    The hot loop of the safety: what no rollout changes is computed once per call, and the draws, the operations
    and their order are those of the plain loop (rng.uniform(a, b) is a + (b - a) * random()), so every number is
    bit-identical to it (tests/inventory_tracking/combat/test_harm_parity.py)."""
    rng = random.Random(settings.seed)
    draw = rng.random
    floor = math.floor
    slots: dict[tuple, int] = {}
    units: dict[int, int] = {}
    steps = []
    for events, protection, start in phases:
        resists, flat, absorb = protection.resists, dict(protection.flat), dict(protection.absorb)
        guarded_kinds = protection.guard.kinds if protection.guard is not None else ()
        for event in events:
            slot = slots.setdefault((event.unit, event.parts, event.melee), len(slots))
            death = deaths.get(event.unit) if deaths else None
            if death is not None and not event.ends > event.begins:
                death = None
            terms = [
                (low, high - low, kind in guarded_kinds, flat.get(kind, 0.0), absorb.get(kind, 0.0), kind)
                for kind, low, high in event.parts
            ]
            # The parts by the rollout's curse + 1, each with the factor its resistance leaves under that curse.
            parts = tuple(tuple((*term[:5], resisted(term[5], resists)[curse]) for term in terms) for curse in range(4))
            steps.append(
                (
                    units.setdefault(event.unit, len(units)), slot, event.blows, event.chance, event.stun,
                    event.stuns, parts, death, start, event.begins, event.ends, event.ends - event.begins,
                )
            )  # fmt: skip
    losses: list[float] = []
    # Points by contributor (`units`' order), None until a blow of its lands: summed in the plain loop's order.
    totals: list[float | None] = [None] * len(units)
    # A curse is shared by all blows in a rollout. No healing promised in advance.
    spread = settings.strike_spread
    never = settings.strike_never / 100
    cursing = 1 - uncursed
    first_pool = phases[0][1].pool
    for _ in range(settings.trials):
        curse = rng.randrange(3) if draw() < cursing else -1
        if amplified and curse < 0 and draw() < amplified:
            curse = 0  # a Cursed hostile's Amplify Damage (CURSED_PRICED); no draw with none: bit-identical
        index = curse + 1
        late = math.inf
        if deaths:
            # How much later than forecast the strikes kill in this rollout, one factor for all (misses, moves).
            roll = draw()
            if roll >= never:
                place_ = roll * (len(spread) - 1)
                low = min(int(place_), len(spread) - 2)
                late = spread[low] + (spread[low + 1] - spread[low]) * (place_ - low)
        pool = first_pool
        clocks: list = [None] * len(slots)
        loss = 0.0
        for unit, slot, blows, chance, stun, stuns, by_curse, death, start, begins, ends, width in steps:
            parts = by_curse[index]
            phase = clocks[slot]
            if phase is None:
                phase = draw()
            # The blows fall where the event's phase crosses a whole number; a stun sets it back.
            remaining = blows
            # min(a, b) is `b if b < a else a` and max(a, b) `b if b > a else a`, as the builtins pick.
            if death is not None:
                # Its blows are spread over [begins, ends] of the dwell; none after the rollout's death.
                dies = death * late - start
                share = ((dies if dies < ends else ends) - begins) / width
                share = share if share > 0.0 else 0.0
                remaining *= share if share < 1.0 else 1.0
            # Past a crossing the phase is a whole number (an int, as floor gives it): the next is 1 ahead.
            up = floor(phase) + 1
            ahead = up - phase
            while not ahead > remaining:
                remaining -= ahead
                phase = up
                up += 1
                ahead = 1
                if draw() >= chance:
                    continue
                points = 0.0
                guarded = pool > 0
                for low, span, guarding, flat_, absorb_, factor in parts:
                    raw = low + span * draw()
                    if guarding:
                        taken = raw if raw < pool else pool
                        pool -= taken
                        raw -= taken
                    after = raw - flat_
                    after = (after if after > 0.0 else 0.0) * factor
                    kept = after - (absorb_ if absorb_ < after else after)
                    points += kept if kept > 0.0 else 0.0
                loss += points
                total = totals[unit]
                totals[unit] = (0.0 if total is None else total) + points
                # Not for the blow that took the pool to 0 (combat/sim/guard.py).
                if stun and guarded and pool > 0 and (stuns >= 1 or draw() < stuns):
                    phase -= stun
                    up = floor(phase) + 1
                    ahead = up - phase
            clocks[slot] = phase + remaining
        losses.append(loss)
    return losses, {unit: total for unit, at in units.items() if (total := totals[at]) is not None}


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
    """The life a look may put at risk over the horizon: what is above the floor, the share of it the potion stock
    keeps (`stock_share`), less the share the pressure takes over the horizon. Insisting on a blocked goal lowers the
    floor as before."""
    floor = max(settings.insist_floor, settings.floor - max(0.0, insisting) * settings.insist_per_second)
    above = max(0.0, life - floor / 100 * most) * stock_share(settings, spendable)
    return above * (1 - min(1.0, pressure.rate * settings.horizon))


def stock_share(settings: SafetySettings, spendable: float | None) -> float:
    """The share of the life budget the potion stock keeps (STOCK_SHARE; the player, 2026-10-14: "the life budget
    scales with the potion stock"; rca/2026-10-14/run-1932-findings.md issue 2). `spendable` in potions of
    `healing_points`; None (belt unread): the whole budget."""
    if spendable is None:
        return 1.0
    curve = settings.stock_share
    potions = spendable / settings.healing_points
    if potions <= curve[0][0]:
        return curve[0][1]
    for (low, at_low), (high, at_high) in pairwise(curve):
        if potions <= high:
            return at_low + (at_high - at_low) * (potions - low) / (high - low)
    return curve[-1][1]


def life_price(supply: Supply, most: float, settings: SafetySettings) -> float:
    if supply.healing:
        return settings.healing_seconds / settings.healing_points
    return settings.rejuvenation_seconds / max(most, 1.0)
