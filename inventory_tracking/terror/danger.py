"""Deadly packs: which groups of live monsters can kill by burst (danger-plan.md; user, 2026-10-06).

A monster's threat is the product of three things (user, 2026-10-07):

- its hit: the type's Hell damage (terror/data/threats.json: multiples of the monster level's
  base damage, physical and elemental apart), raised by its own modifiers (monster data +0x20..,
  inherited ones on minions, the Terror Zone's forced one on plain monsters), the aura it stands
  in (stat 350 on first sight, or an aura owner within the aura's range) and curses nearby;
- its rate: Extra Fast, Fanatic, Multiple Shots;
- its reach: whether the hit lands at all. A ranged attacker's does, from off screen, so it
  counts in full. A melee attacker has to catch the player: one no faster than `still` never
  does and scores nothing whatever raises its hit (zombies, skeletons), one as fast as the
  player's run always does, and of those only a few stand next to the player at once. Extra
  Fast, Teleportation and a Holy Freeze on the player are what turn slow melee into a threat.

The player's own states (monsters.py `player_states`) count as facts, for every pack: Amplify
Damage and Decrepify raise physical damage, Lower Resist and Conviction elemental, and a frozen,
decrepified or Holy Frozen player is reached by melee (a chill is not counted: marked Ghoul packs
took 0.29% of the life a second with it and 0.68% without, probe logs to 2026-10-07). A curse or
Conviction that is on the player is not counted again for its source standing near, which is only
the guess made before it lands.

Monsters within LINK of each other are one pack and its score is the sum, so density is the
score itself: two archer packs standing together are one deadly pack.

The factors are estimates, not the game's formulas, and the bands are set so that plain packs
stay unmarked. They are to be tuned from burst events once the probe logs carry the player's
life (terror/bursts.py). Pure data and arithmetic: no memory reads, no GTK.
"""

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from inventory_tracking.config import Config


DATA = Path(__file__).parent / 'data' / 'threats.json'

# monumod.txt ids
STRONG, FAST, CURSED, FIRE, LIGHTNING, COLD, TELEPORT, MULTISHOT, FANATIC, BERSERKER = (
    5,
    6,
    7,
    9,
    17,
    18,
    26,
    29,
    37,
    39,
)
# skills.txt ids of the auras (threats.json `auras`)
MIGHT, BLESSED_AIM, FANATICISM, CONVICTION, HOLY_FREEZE, HOLY_FIRE, HOLY_SHOCK = 98, 108, 122, 123, 365, 368, 369
# states.txt ids, on the player
FROZEN, AMPLIFIED, CHILLED, SLOWED, CONVICTED, HOLY_FROZEN, DECREPIFIED, LOWER_RESIST = 1, 9, 11, 24, 29, 44, 60, 61
STATES = {
    FROZEN: 'Frozen', AMPLIFIED: 'Amplify Damage on you', CHILLED: 'Chilled', SLOWED: 'Slowed',
    CONVICTED: 'Conviction', HOLY_FROZEN: 'Holy Freeze', DECREPIFIED: 'Decrepify on you',
    LOWER_RESIST: 'Lower Resist on you',
}  # fmt: skip
AIMED_AT_PLAYER = frozenset((CONVICTION, HOLY_FREEZE))  # never a stat on monsters: they act on the player


class DangerConfig(Config):
    # Pack scores from which a pack is marked. Replay of the 50 probe logs to 2026-10-06 (first-sight
    # positions, the three highest packs every 3 s): 16% of those packs reach 9, 9.6% reach 12.
    caution: float = 9.0
    deadly: float = 12.0
    # A pack marked on the last pass keeps its mark down to this share of the score that gives
    # it: a kill, a step out of an aura or a pack splitting no longer toggles it (user, 2026-10-06).
    release: float = 0.75
    reason_share: float = 0.15  # a reason is named when it is behind this share of the pack's score
    link: float = 30.0  # world units: monsters this close are one pack (6 tiles)
    # An aura that acts on the player (Conviction, Holy Freeze) counts for monsters this near its
    # owner, about a screen: whoever fights them stands in it.
    player_aura_reach: float = 60.0
    curse_reach: float = 60.0  # a Cursed monster or a curse caster this near raises physical damage
    # The share of elemental damage that gets through: resistances at the Hell cap of 75%. To be
    # replaced by the character's own resistances (danger-plan.md, phase 6).
    resisted: float = 0.25
    melee: float = 0.5  # the share of a ranged one's threat of a melee attacker that reaches the player
    melee_count: int = 8  # melee attackers of a pack that reach the player at once
    # Reach of a melee attacker by its speed (monstats Velocity / Run, the unit of the player's
    # own 6 walking and 9 running): none up to `still`, full from `player_run`, linear between.
    still: float = 3.0  # zombies, skeletons, mummies, brutes
    player_run: float = 9.0
    # Extra Fast: movement speed factor (an estimate). Was 2.0: Extra Fast Ghouls were the most
    # marked packs of the probe logs to 2026-10-07 at a quarter of the other marked packs' life lost.
    fast_move: float = 1.5
    slowed: float = 0.7  # the player's run under Holy Freeze
    arrives: float = (
        0.5  # the least reach of one that teleports, charges or leaps: it arrives, then hits at its own pace
    )
    frenzy: float = 1.5  # attacks per second factor of a Frenzy user
    # Families (monstats BaseId) or single types (by name, which comes first) whose hit is not
    # their monstats number, as a factor on it. Souls: four
    # plain Gloams took 18% of the life within a second (probe log 20261006T161833Z, area 77),
    # as much as fourteen slingers under Fanaticism in the same log.
    # Abyss Knights: six took 18% twice at a score of 8.4 (20261006T175752Z, area 107); their bolt
    # is a skill, the number a stand-in. Undead dolls blow up when killed (no log event: an estimate).
    # From the `around` samples to 2026-10-07 (77 minutes, Catacombs 2-4; exposure.py): where Tainted
    # were the highest pack 2.1 times the life of other types at the same score went unwarned and
    # 3.5 times warned, and they stood in 12 of the 21 seconds that took 15%, while the Afflicted
    # of the same family and numbers lost 0.8 times. Dark Ones: 0.2 times the model's average
    # per monster over 27,720 monster-seconds.
    hard: Mapping[str, float] = {
        'willowisp1': 5.0, 'doomknight2': 1.25, 'bonefetish1': 2.0, 'Tainted': 2.0, 'fallen1': 0.5,
    }  # fmt: skip
    # Own modifier -> physical damage factor. Extra Strong was 2.0: packs named for it lost 0.7
    # times the life of others at their score (392 s, the same samples).
    physical: Mapping[int, float] = {STRONG: 1.5, BERSERKER: 2.0}
    speed: Mapping[int, float] = {FAST: 1.25, FANATIC: 1.25}  # own modifier -> attacks per second factor
    added: Mapping[int, float] = {FIRE: 0.5, LIGHTNING: 0.5, COLD: 0.3}  # own modifier -> elemental damage added
    multishot: float = 2.0  # Multiple Shots on a ranged attacker
    aura_physical: Mapping[int, float] = {MIGHT: 2.0, FANATICISM: 1.75, BLESSED_AIM: 1.2}
    aura_added: Mapping[int, float] = {HOLY_FIRE: 0.3, HOLY_SHOCK: 0.4}  # elemental damage added to each attack
    conviction: float = 3.0  # elemental damage factor: resistances 75% -> about 25% at aura level 9
    holy_freeze: float = 1.2  # everything: the player is slowed
    curse: float = 1.5  # physical damage factor near a curse source (Amplify Damage, Decrepify)
    # The player's own states. Physical: Amplify Damage takes 100% of the physical resistance,
    # Decrepify 50%. Elemental: Lower Resist takes about as much resistance as Conviction.
    # Amplify Damage was 2.0: packs named for it lost 0.6 times the life of others at their score
    # (552 s of the `around` samples to 2026-10-07).
    player_physical: Mapping[int, float] = {AMPLIFIED: 1.5, DECREPIFIED: 1.5}
    player_elemental: Mapping[int, float] = {LOWER_RESIST: 2.5}
    player_slowed: tuple[int, ...] = (DECREPIFIED, HOLY_FROZEN, FROZEN, SLOWED)  # the first found is named


DANGER = DangerConfig()
BANDS = ('caution', 'deadly')  # the weaker first


@dataclass(frozen=True)
class Threat:
    name: str
    family: str
    physical: float
    elemental: float  # fire, lightning, cold: cut by the player's resistances
    magic: float = 0.0  # magic damage: neither resisted nor raised by physical auras
    ranged: bool = False
    curses: tuple[str, ...] = ()
    speed: float = 0.0  # the faster of walk and run; the player walks at 6 and runs at 9
    closes: bool = False  # Charge, Leap: it arrives whatever its speed
    frenzy: bool = False


@dataclass(frozen=True)
class Table:
    monsters: dict[int, Threat]
    auras: dict[int, tuple[str, int, int]]  # skill id -> name, range at level 1, range per level
    modifiers: dict[int, str]

    def aura_range(self, skill: int, level: int) -> float:
        base, per_level = self.auras[skill][1:]
        return base + max(level - 1, 0) * per_level


@cache
def table(path: Path = DATA) -> Table:
    data = json.loads(path.read_text(encoding='utf-8'))
    monsters = {
        int(txt_id): Threat(
            row['name'], row['family'], row['physical'], row['elemental'], row.get('magic', 0.0),
            row.get('ranged', False), tuple(row.get('curses', ())), row.get('speed', 0.0),
            row.get('closes', False), row.get('frenzy', False),
        )
        for txt_id, row in data['monsters'].items()
    }  # fmt: skip
    auras = {int(skill): (row['name'], *row['range']) for skill, row in data['auras'].items()}
    return Table(monsters, auras, {int(mod): name for mod, name in data['modifiers'].items()})


@dataclass(frozen=True)
class Unit:
    """A live hostile monster: position in world units, and what it showed on first sight."""

    unit_id: int
    txt_id: int
    x: float
    y: float
    modifiers: tuple[int, ...] = ()  # monumod ids, monster data +0x20..
    aura: tuple[int, int] | None = None  # (skill, level) of stats 350/351 when the skill is an aura
    owner: bool = False  # aura enchanted: the aura is its own


@dataclass(frozen=True)
class Pack:
    members: tuple[int, ...]  # unit ids
    score: float
    band: str | None  # 'deadly', 'caution' or None
    name: str  # the type carrying most of the score
    count: int  # monsters of that type
    reasons: tuple[str, ...]  # what raised the score, the strongest first
    x: float  # the score's centre, world units
    y: float

    @property
    def label(self) -> str:
        return ' · '.join((f'{self.name} x{self.count}', *self.reasons))


def near(a: Unit, b: Unit, reach: float) -> bool:
    return math.hypot(a.x - b.x, a.y - b.y) <= reach


def threat(
    unit: Unit, units, threats: Table, config: DangerConfig, player=frozenset()
) -> tuple[float, dict[str, float]]:
    """(threat, reason -> the factor it raised the threat by) of one monster among `units`, for a
    player with the states `player` (states.txt ids)."""
    row = threats.monsters.get(unit.txt_id)
    if row is None:
        return 0.0, {}
    reasons: dict[str, float] = {}

    def apply(value: float, factor: float, name: str) -> float:
        if value and factor != 1:
            reasons[name] = reasons.get(name, 1.0) * factor
        return value * factor

    hard = config.hard.get(row.name, config.hard.get(row.family, 1))
    physical, elemental, magic = row.physical * hard, row.elemental * hard * config.resisted, row.magic * hard
    auras = {unit.aura[0]} if unit.aura and not unit.owner else set()
    for other in units:
        if other.owner and other.aura:
            skill, level = other.aura
            reach = config.player_aura_reach if skill in AIMED_AT_PLAYER else threats.aura_range(skill, level)
            if near(unit, other, reach):
                auras.add(skill)
    for modifier in unit.modifiers:
        name = threats.modifiers.get(modifier, str(modifier))
        physical = apply(physical, config.physical.get(modifier, 1), name)
        if modifier in config.added:
            before = physical + elemental + magic
            elemental += config.added[modifier] * config.resisted
            reasons[name] = (before + config.added[modifier] * config.resisted) / before if before else 1.0
    for skill in sorted(auras):
        name = threats.auras[skill][0]
        physical = apply(physical, config.aura_physical.get(skill, 1), name)
        if skill in config.aura_added:
            before = physical + elemental + magic
            elemental += config.aura_added[skill] * config.resisted
            reasons[name] = (before + config.aura_added[skill] * config.resisted) / before if before else 1.0
    if CONVICTION in auras or CONVICTED in player:
        elemental = apply(elemental, config.conviction, threats.auras[CONVICTION][0])
    for state in sorted(player):
        elemental = apply(elemental, config.player_elemental.get(state, 1), STATES.get(state, str(state)))
    cursers = [o for o in units if near(unit, o, config.curse_reach)]
    if cursed := [state for state in sorted(player) if state in config.player_physical]:
        worst = max(cursed, key=lambda state: config.player_physical[state])
        physical = apply(physical, config.player_physical[worst], STATES[worst])
    elif any(CURSED in o.modifiers for o in cursers):
        physical = apply(physical, config.curse, threats.modifiers.get(CURSED, 'Cursed'))
    elif curses := [c for o in cursers if (found := threats.monsters.get(o.txt_id)) for c in found.curses]:
        physical = apply(physical, config.curse, curses[0])
    total = (physical + elemental + magic) * (config.frenzy if row.frenzy else 1)
    for modifier in unit.modifiers:
        total = apply(total, config.speed.get(modifier, 1), threats.modifiers.get(modifier, str(modifier)))
        if modifier == MULTISHOT and row.ranged:
            total = apply(total, config.multishot, threats.modifiers.get(modifier, 'Multiple Shots'))
    if HOLY_FREEZE in auras:
        total = apply(total, config.holy_freeze, threats.auras[HOLY_FREEZE][0])
    if row.ranged:
        return total, reasons
    slow = threats.auras[HOLY_FREEZE][0] if HOLY_FREEZE in auras else None
    slow = slow or next((STATES[state] for state in config.player_slowed if state in player), None)
    return total * config.melee * melee_reach(unit, row, slow, threats, config, reasons), reasons


def melee_reach(unit: Unit, row: Threat, slow: str | None, threats: Table, config: DangerConfig, reasons) -> float:
    """The share of a melee attacker's hits that land, 0..1: by its speed against the player's.
    What raised it is added to `reasons` (all of it, for a monster that had no reach without)."""

    def share(speed: float, run: float) -> float:
        return min(max((speed - config.still) / (run - config.still), 0.0), 1.0)

    found = max(share(row.speed, config.player_run), config.arrives if row.closes else 0.0)
    steps = []  # (reason, the reach with it)
    speed, run = row.speed, config.player_run
    if FAST in unit.modifiers:
        speed *= config.fast_move
        steps.append((threats.modifiers.get(FAST, 'Extra Fast'), share(speed, run)))
    if slow:  # what slows the player
        run *= config.slowed
        steps.append((slow, share(speed, run)))
    if TELEPORT in unit.modifiers:
        steps.append((threats.modifiers.get(TELEPORT, 'Teleportation'), config.arrives))
    for name, raised in steps:
        if raised > found:
            reasons[name] = reasons.get(name, 1.0) * (raised / found if found else math.inf)
            found = raised
    return found


def clusters(units, link: float) -> list[list[Unit]]:
    """Single-link groups: a chain of monsters each within `link` of the next is one pack."""
    cells: dict[tuple[int, int], list[Unit]] = {}
    for unit in units:
        cells.setdefault((int(unit.x // link), int(unit.y // link)), []).append(unit)
    seen, groups = set(), []
    for start in units:
        if start.unit_id in seen:
            continue
        seen.add(start.unit_id)
        group, queue = [], [start]
        while queue:
            unit = queue.pop()
            group.append(unit)
            cx, cy = int(unit.x // link), int(unit.y // link)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for other in cells.get((cx + dx, cy + dy), ()):
                        if other.unit_id not in seen and near(unit, other, link):
                            seen.add(other.unit_id)
                            queue.append(other)
        groups.append(group)
    return groups


def band_of(score: float, counted, held: Mapping[int, str], config: DangerConfig) -> str | None:
    """The pack's band: by its score, or the one most of it (by score) was marked with before,
    while the score stays above that band's release."""
    for rank, band in reversed(tuple(enumerate(BANDS))):
        line = getattr(config, band)
        kept = sum(value for unit, value, _ in counted if held.get(unit.unit_id) in BANDS[rank:])
        if score >= line or (score >= config.release * line and kept * 2 >= score):
            return band
    return None


def packs(
    units,
    *,
    threats: Table | None = None,
    config: DangerConfig = DANGER,
    held: Mapping[int, str] | None = None,
    player=frozenset(),
) -> list[Pack]:
    """The packs among `units` (live hostile monsters of one level), the highest score first.
    `held`: unit id -> the band its pack had on the last pass; `player`: the states on the
    player (states.txt ids)."""
    player = frozenset(player)
    threats = threats or table()
    units = list(units)
    result = []
    for group in clusters(units, config.link):
        scored = [(unit, *threat(unit, units, threats, config, player)) for unit in group]
        ranged = [s for s in scored if s[1] and threats.monsters[s[0].txt_id].ranged]
        melee = sorted((s for s in scored if s[1] and not threats.monsters[s[0].txt_id].ranged), key=lambda s: -s[1])[
            : config.melee_count
        ]
        counted = ranged + melee
        score = sum(found[1] for found in counted)
        if not score:
            continue
        by_name: dict[str, list[float]] = {}
        raised: dict[str, float] = {}
        for unit, value, reasons in counted:
            by_name.setdefault(threats.monsters[unit.txt_id].name, []).append(value)
            for reason, factor in reasons.items():
                if factor > 1:  # the part of the score this reason is behind
                    raised[reason] = raised.get(reason, 0.0) + value * (1 - 1 / factor)
        name = max(by_name, key=lambda n: sum(by_name[n]))
        band = band_of(score, counted, held or {}, config)
        count = sum(row is not None and row.name == name for row in (threats.monsters.get(u.txt_id) for u in group))
        named = [reason for reason in raised if raised[reason] >= config.reason_share * score]
        reasons = tuple(sorted(named, key=lambda reason: -raised[reason]))
        x = sum(unit.x * value for unit, value, _ in counted) / score
        y = sum(unit.y * value for unit, value, _ in counted) / score
        members = tuple(sorted(unit.unit_id for unit in group))
        result.append(Pack(members, round(score, 2), band, name, count, reasons, x, y))
    return sorted(result, key=lambda pack: -pack.score)
