"""Layer 1 of the loot design (loot/design.md §1.1): what an item is, as read. Pure.

`ItemFacts` holds the base (items.txt code and itemtypes code, from items/metadata.py, never typed), the quality, the
identified flag, ethereal and sockets, and the rolls as raw memory values keyed 'stat id:layer' (itemstatcost ids,
`appraisal/owned.py` `stat_key`'s keys). A field that was not read is None, never a guess; `known` names the stat ids
a partial read covers (a ground read covers only a base's rolls: game/decode.py `base_rolls`), so an absent stat of a
full read is 0 and one outside a partial read is unknown.

Adapters: `from_drop` (a ground `Drop` and its `Rolls`), `from_carried` (a carried `Carried`, with its identify read
when there is one), `from_observation` (an identify or collection read).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from functools import cache
from typing import Any

from inventory_tracking.game.records import Carried, Drop
from inventory_tracking.items.metadata import item_base, metadata


__all__ = [
    'CRAFTED',
    'GROUND_STATS',
    'LOW',
    'MAGIC',
    'NORMAL',
    'QUALITY_NAMES',
    'RARE',
    'SET',
    'SUPERIOR',
    'UNIQUE',
    'ItemFacts',
    'Owner',
    'Where',
    'base_of_code',
    'from_carried',
    'from_drop',
    'from_observation',
    'quality_of',
]

# ItemData quality (loot/shown.py RARITIES; 8 crafted)
LOW, NORMAL, SUPERIOR, MAGIC, SET, RARE, UNIQUE, CRAFTED = 1, 2, 3, 4, 5, 6, 7, 8
QUALITY_NAMES = {
    LOW: 'low',
    NORMAL: 'normal',
    SUPERIOR: 'superior',
    MAGIC: 'magic',
    SET: 'set',
    RARE: 'rare',
    UNIQUE: 'unique',
    CRAFTED: 'crafted',
}
# Stat ids (third-parties/d2data/json/itemstatcost.json, checked 2026-10-20)
SOCKETS, SINGLE_SKILL, DEFENSE_PERCENT, DAMAGE_PERCENT, SKILL_TAB = 194, 107, 16, 17, 188
RESISTS = (39, 41, 43, 45)  # fire, lightning, cold, poison
# The stat ids a ground read of a white or superior base holds (game/decode.py `base_rolls`): sockets, staff mods,
# resists, and armor enhanced defense (16) once its +0xD0 modifier chain is read whole (`Rolls.defense` not None;
# 2026-10-20: the read took 16 from the totals, where this build never keeps it, rca/2026-10-20/loot-m0-research.md
# R2). Since M5 (2026-10-20) a superior weapon's enhanced damage (17, the same chain) and the skill tab bonuses (188:
# a white bow's +3 Bow and Crossbow Skills, in the totals)
GROUND_STATS = frozenset((SOCKETS, SINGLE_SKILL, *RESISTS, DEFENSE_PERCENT, DAMAGE_PERCENT, SKILL_TAB))


class Where(StrEnum):
    GROUND = 'ground'
    INVENTORY = 'inventory'
    CUBE = 'cube'
    STASH = 'stash'
    EQUIPPED = 'equipped'


class Owner(StrEnum):
    LOOP = 'loop'  # a volatile cell or the cube (macros/volatile.py): the only items any action may touch
    PLAYER = 'player'  # a protected cell, a print match, equipment, the stash
    UNKNOWN = 'unknown'  # not told yet: treated as PLAYER (S1)


@dataclass(frozen=True)
class ItemFacts:
    """What an item is, as read. Unread fields are None, never a guess."""

    unit_id: int
    code: str  # items.txt code ('uit'), from items/metadata.py
    base_type: str  # itemtypes code ('shie', 'knif', 'pole'...)
    size: tuple[int, int]
    quality: int  # ItemData quality: 1 low ... 8 crafted
    identified: bool
    ethereal: bool | None
    sockets: int | None  # stat 194; None unread
    rolls: Mapping[str, int] | None  # 'id:layer' -> raw value; None unread
    name: str | None = None  # unique/set/rare name once identified
    row: int | None = None  # uniqueitems/setitems row (ItemData +0x34) once identified
    where: Where = Where.GROUND
    owner: Owner = Owner.UNKNOWN
    cell: tuple[int, int] | None = None
    page: int | None = None  # stash page (0 personal, 1..5 shared)
    txt: int | None = None  # items.txt row (the class id the game reads)
    base_name: str = ''
    known: frozenset[int] | None = None  # the stat ids a partial read covers; None: the full list
    marked: bool = False  # the loot marks point at it (Drop.prized)
    # Its runeword's name when the read says it is one (the identify read's item['runeword']; D12, 2026-10-23), or
    # BY_FLAG when only the game's flag says so (the ground and carried reads, items/identity.py RUNEWORD_FLAG): never
    # a plain base
    runeword: str | None = None
    observation: Mapping[str, Any] | None = field(default=None, compare=False, repr=False)

    @property
    def quality_name(self) -> str:
        return QUALITY_NAMES.get(self.quality, 'unread')

    def stat(self, stat_id: int, layer: int = 0) -> int | None:
        """The raw value of a stat; 0 when a read that covers it lacks it; None when not read."""
        if self.rolls is None or (self.known is not None and stat_id not in self.known):
            return None
        return self.rolls.get(f'{stat_id}:{layer}', 0)

    def stat_any(self, stat_id: int, layers: Iterable[int] | None = None) -> int | None:
        """The most of a layered stat over `layers` (None: every layer read)."""
        if self.rolls is None or (self.known is not None and stat_id not in self.known):
            return None
        wanted = None if layers is None else {f'{stat_id}:{layer}' for layer in layers}
        prefix = f'{stat_id}:'
        values = [v for k, v in self.rolls.items() if k.startswith(prefix) and (wanted is None or k in wanted)]
        return max(values, default=0)

    def facet(self, key: str) -> Any:
        """A named facet for the wants' conditions: 'ethereal', 'sockets', 'quality', 'identified'."""
        if key == 'ethereal':
            return self.ethereal
        if key == 'sockets':
            return self.sockets
        if key == 'quality':
            return self.quality_name
        if key == 'identified':
            return self.identified
        raise KeyError(key)

    def title(self) -> str:
        """'Goblin Toe (Light Plated Boots)', 'magic Monarch 4os', 'normal Kriss 3os' for the log."""
        base = self.base_name or self.code
        if self.name and self.name != base:
            return f'{self.name} ({base})'
        sockets = f' {self.sockets}os' if self.sockets else ''
        eth = ' eth' if self.ethereal else ''
        return f'{self.quality_name}{eth} {base}{sockets}'


@cache
def _bases_by_code() -> dict[str, tuple[int, dict[str, Any]]]:
    return {row['code']: (int(txt), row) for txt, row in metadata()['bases'].items() if row.get('code')}


def base_of_code(code: str) -> tuple[int, dict[str, Any]] | None:
    """(class id, base row) of an items.txt code; None for a code the game data lacks."""
    return _bases_by_code().get(code)


def quality_of(name: str | None) -> int:
    """ItemData quality of a rarity word ('superior' or 'hiQuality'); 0 unknown."""
    words = {v: k for k, v in QUALITY_NAMES.items()} | {'hiQuality': SUPERIOR, 'lowQuality': LOW}
    return words.get(name or '', 0)


def _ground_rolls(drop: Drop) -> dict[str, int] | None:
    found = drop.rolls
    if found is None:
        return None
    if drop.quality >= MAGIC:
        return {}  # an unidentified item holds only its base stats: no affix, no socket count (R1)
    rolls = {f'{SOCKETS}:0': found.sockets}
    rolls |= {f'{SINGLE_SKILL}:{skill}': level for skill, level in found.skills}
    # The read keeps the least of the four resistances: each is at least that (Sacred Targe's all-res rule)
    rolls |= {f'{stat}:0': found.resists for stat in RESISTS}
    rolls |= {f'{SKILL_TAB}:{layer}': value for layer, value in found.tabs}
    if found.defense is not None:
        rolls[f'{DEFENSE_PERCENT}:0'] = found.defense
    if found.damage is not None:
        rolls[f'{DAMAGE_PERCENT}:0'] = found.damage
    return rolls


def _ground_known(drop: Drop) -> frozenset[int] | None:
    """The stat ids the ground read covers: none for magic and better (R1); the ED only when its chain was read."""
    found = drop.rolls
    if found is None:
        return None
    if drop.quality >= MAGIC or drop.quality <= 0:
        return frozenset()
    unread = {DEFENSE_PERCENT} if found.defense is None else set()
    unread |= {DAMAGE_PERCENT} if found.damage is None else set()
    return GROUND_STATS - unread


# A runeword the game's flag marks whose name no read gave (game/records.py Carried.runeword, Rolls.runeword; D12)
BY_FLAG = 'by the game flag'


def from_drop(drop: Drop) -> ItemFacts:
    """A ground drop's facts: quality, base, and its base rolls when the ground read has them (`Drop.rolls`; only
    the base types game/layout.py ROLLED_TYPES names). Magic and better on the ground are unidentified, and their
    stat lists hold no affix and no socket count until identified (R1, rca/2026-10-20/loot-m0-research.md): only
    the ethereal flag is read for them."""
    base = item_base(drop.txt) if drop.txt else None
    rolls = _ground_rolls(drop)
    white = 0 < drop.quality < MAGIC
    return ItemFacts(
        unit_id=drop.unit_id,
        code=base['code'] if base else '',
        base_type=base['type'] if base else '',
        size=drop.size,
        quality=drop.quality,
        identified=0 < drop.quality <= SUPERIOR,
        ethereal=drop.rolls.ethereal if drop.rolls is not None else None,
        sockets=drop.rolls.sockets if drop.rolls is not None and white else None,
        rolls=rolls,
        where=Where.GROUND,
        owner=Owner.UNKNOWN,
        txt=drop.txt or None,
        base_name=base['name'] if base else drop.label,
        known=_ground_known(drop),
        marked=drop.prized,
        runeword=BY_FLAG if drop.rolls is not None and drop.rolls.runeword else None,
    )


def _observed_rolls(observation: Mapping[str, Any]) -> dict[str, int]:
    rolls: dict[str, int] = {}
    for row in observation.get('decoded_stats', ()):
        stats = [row['memory_stat']] if row.get('memory_stat') else row.get('memory_stats') or []
        for stat in stats:
            if isinstance(stat, Mapping) and 'id' in stat and 'layer' in stat and isinstance(stat.get('raw'), int):
                rolls[f'{stat["id"]}:{stat["layer"]}'] = stat['raw']
    return rolls


def from_observation(
    observation: Mapping[str, Any],
    *,
    where: Where = Where.STASH,
    owner: Owner = Owner.PLAYER,
    unit_id: int | None = None,
    cell: tuple[int, int] | None = None,
    txt: int | None = None,
    size: tuple[int, int] | None = None,
) -> ItemFacts:
    """An identify or collection read's facts (`observation`: item, source, decoded_stats)."""
    item = observation.get('item') or {}
    source = observation.get('source') or {}
    code = item.get('base_code') or ''
    known = base_of_code(code)
    identity = source.get('item_identity') or {}
    unit = unit_id if unit_id is not None else source.get('unit_id')
    sockets = item.get('sockets')
    return ItemFacts(
        unit_id=int(unit) if isinstance(unit, int | str) and str(unit).isdigit() else 0,
        code=code,
        base_type=known[1]['type'] if known else item.get('item_type') or '',
        size=size or (1, 1),
        quality=quality_of(item.get('rarity')),
        identified=item.get('identified') is not False,
        ethereal=item.get('ethereal'),
        sockets=sockets if isinstance(sockets, int) else None,
        rolls=_observed_rolls(observation),
        name=item.get('name'),
        row=identity.get('table_id') if isinstance(identity.get('table_id'), int) else None,
        where=where,
        owner=owner,
        cell=cell,
        txt=txt if txt is not None else (known[0] if known else None),
        base_name=item.get('base_name') or (known[1]['name'] if known else ''),
        runeword=item.get('runeword') or None,
        observation=observation,
    )


def from_carried(
    item: Carried,
    *,
    owner: Owner,
    where: Where = Where.INVENTORY,
    observation: Mapping[str, Any] | None = None,
    stats: Mapping[int, int] | None = None,
) -> ItemFacts:
    """A carried item's facts: from its identify read when there is one (`observation`), else its class and quality,
    with `stats` ({stat id: raw}, layer 0: World.item_stats) as its rolls when read."""
    cell = (item.x, item.y)
    if observation is not None:
        facts = from_observation(
            observation, where=where, owner=owner, unit_id=item.unit_id, cell=cell, txt=item.txt, size=item.size
        )
        return replace(facts, runeword=BY_FLAG) if item.runeword and not facts.runeword else facts
    base = item_base(item.txt)
    rolls = {f'{stat}:0': value for stat, value in stats.items()} if stats else None
    return ItemFacts(
        unit_id=item.unit_id,
        code=base['code'] if base else '',
        base_type=base['type'] if base else '',
        size=item.size,
        quality=item.quality,
        identified=item.identified,
        ethereal=None,
        sockets=stats.get(SOCKETS, 0) if stats else None,
        rolls=rolls,
        row=item.unique or None,
        where=where,
        owner=owner,
        cell=cell,
        txt=item.txt,
        base_name=base['name'] if base else f'item {item.txt}',
        runeword=BY_FLAG if item.runeword else None,
    )
