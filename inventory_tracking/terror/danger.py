"""Deadly packs: which groups of live monsters can kill by burst (danger-plan.md; user, 2026-10-06).

A monster's threat = hit x rate x reach (user, 2026-10-07). Hit: the type's Hell damage
(data/threats.json) raised by rank, modifiers, auras and curses. Rate: Extra Fast, Fanatic,
Multiple Shots. Reach: a ranged hit counts in full; melee by its speed against the player's run.
The player's own states (monsters.py `player_states`) count as facts for every pack.
Monsters within `link` of each other are one pack, scored by the sum. The factors are estimates
tuned from the probe logs (danger-plan.md); pure data and arithmetic, no memory reads, no GTK.
"""

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from inventory_tracking.config import Config
from inventory_tracking.game.layout import LEADER_FLAGS, MINION_FLAG


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
    # Pack scores from which a pack is marked (probe-log replay, danger-plan.md).
    caution: float = 9.0
    deadly: float = 12.0
    # A marked pack keeps its mark down to this share of its band, so it does not toggle (user, 2026-10-06).
    release: float = 0.75
    reason_share: float = 0.15  # a reason is named when it is behind this share of the pack's score
    link: float = 30.0  # world units: monsters this close are one pack (6 tiles)
    # A player-aimed aura (Conviction, Holy Freeze) counts for monsters this near its owner (about a screen).
    player_aura_reach: float = 60.0
    curse_reach: float = 60.0  # a Cursed monster or a curse caster this near raises physical damage
    resisted: float = 0.25  # elemental share that gets through: 75% Hell-cap resistances (danger-plan.md phase 6)
    melee: float = 0.5  # the share of a ranged one's threat of a melee attacker that reaches the player
    melee_count: int = 8  # melee attackers of a pack that reach the player at once
    # Melee reach by speed (monstats Velocity / Run; the player walks 6, runs 9): none up to
    # `still`, full from `player_run`, linear between.
    still: float = 3.0  # zombies, skeletons, mummies, brutes
    player_run: float = 9.0
    fast_move: float = 1.5  # Extra Fast movement factor, an estimate (2.0 overrated, danger-plan.md)
    slowed: float = 0.7  # the player's run under Holy Freeze
    arrives: float = (
        0.5  # the least reach of one that teleports, charges or leaps: it arrives, then hits at its own pace
    )
    frenzy: float = 1.5  # attacks per second factor of a Frenzy user
    # Factor on the monstats hit of families (BaseId) or single types (by name, checked first)
    # that hit harder or softer than their number; evidence per entry in danger-plan.md.
    hard: Mapping[str, float] = {
        'willowisp1': 5.0, 'doomknight2': 1.25, 'bonefetish1': 2.0, 'Tainted': 2.0, 'fallen1': 0.5,
    }  # fmt: skip
    physical: Mapping[int, float] = {STRONG: 1.5, BERSERKER: 2.0}  # own modifier -> physical damage factor
    speed: Mapping[int, float] = {FAST: 1.25, FANATIC: 1.25}  # own modifier -> attacks per second factor
    # An elemental enchantment adds a share of the monster's own physical hit: monumod.txt
    # "Elemental Min..Max Damage % Bonus (Hell)", the middle of 66..100 (unique) and 33..50 (others).
    elements: tuple[int, ...] = (FIRE, LIGHTNING, COLD)
    enchanted: float = 0.415
    enchanted_unique: float = 0.83
    leader: float = 1.66  # unique / champion hit: difficultylevels.txt Hell Unique/ChampionDamageBonus 66
    # A Herald's and its minions' hit by tier: installed game's TZ config (terror_zones/data).
    herald: Mapping[int, float] = {1: 1.5, 2: 1.75, 3: 2.0, 4: 2.25, 5: 2.5}
    herald_minion: Mapping[int, float] = {1: 1.1, 2: 1.2, 3: 1.3, 4: 1.4, 5: 1.5}
    multishot: float = 2.0  # Multiple Shots on a ranged attacker
    aura_physical: Mapping[int, float] = {MIGHT: 2.0, FANATICISM: 1.75, BLESSED_AIM: 1.2}
    aura_added: Mapping[int, float] = {HOLY_FIRE: 0.3, HOLY_SHOCK: 0.4}  # elemental damage added to each attack
    conviction: float = 3.0  # elemental damage factor: resistances 75% -> about 25% at aura level 9
    holy_freeze: float = 1.2  # everything: the player is slowed
    curse: float = 1.5  # physical damage factor near a curse source (Amplify Damage, Decrepify)
    # The player's own states: Amplify Damage / Decrepify raise physical damage, Lower Resist about
    # as much as Conviction (tuned down from 2.0, danger-plan.md).
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
    flags: int = 0  # the type flags of the monster data (+0x1A): unique, champion, minion
    tier: int = 0  # stat 367: the tier of the Herald it is, or whose minion it is; 0 for neither

    @property
    def minion(self) -> bool:
        return bool(self.flags & MINION_FLAG)

    @property
    def leader(self) -> bool:
        """A unique, a super unique or a champion itself."""
        return bool(self.flags & LEADER_FLAGS) and not self.minion


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
    hard *= config.leader if unit.leader else 1  # not named: every pack leader has it
    physical, elemental, magic = row.physical * hard, row.elemental * hard * config.resisted, row.magic * hard
    if unit.tier:
        boost = (config.herald_minion if not unit.leader else config.herald).get(unit.tier, 1)
        physical, elemental, magic = physical * boost, elemental * boost, magic * boost
        if boost != 1 and physical + elemental + magic:
            reasons['Herald' if unit.leader else "Herald's minion"] = boost
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
    for modifier in unit.modifiers:  # after all that raises the physical hit: the enchantment adds a share of it
        if modifier in config.elements and physical:
            before = physical + elemental + magic
            added = physical * (config.enchanted_unique if unit.leader else config.enchanted) * config.resisted
            elemental += added
            reasons[threats.modifiers.get(modifier, str(modifier))] = (before + added) / before
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
    """The share of a melee attacker's hits that land, 0..1, by its speed against the player's;
    what raised it is added to `reasons`."""

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
