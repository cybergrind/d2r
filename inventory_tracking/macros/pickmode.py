"""The KP_6 loop's pickup mode (routes/lower-kurast-loop-plan.md phase 7), switched by a double press of KP_6.

The player, 2026-10-16: "by default only 100% valuables (rare rings, known good uniques, all runes, all gems, all
charms). and can switch for pickup regular - what do we have right now"; and "we pickup gold, we need it to repair our
staff of teleportation".

- `SURE` (the default): of what the regular pickup takes, only the sure valuables. Every rune, gem and charm; a rare
  ring; a unique or set item the loot marks price (`source` 'unique': loot/data/uniques.json at `unique_minimum` Ist
  and up). The supplies stay in both modes: gold, and the potions the belt is short of.
- `REGULAR`: today's pickup, untouched (macros/pickup.py `wanted`, `choose`).

A filter over the drops the regular rules found (`kept`), so no rule is written twice: the sure mode never takes what
the regular one would not. The item types are the game's own (items/metadata.py `item_base`: misc.txt's type column),
listed from the bundled metadata on 2026-10-16, not written from memory.
"""

from dataclasses import replace

from inventory_tracking.items.metadata import item_base
from inventory_tracking.loot.shown import RARITIES
from inventory_tracking.macros.world import VALUABLE, Drop, Loot


__all__ = ['MODES', 'REGULAR', 'SURE', 'kept', 'next_mode', 'sure']

SURE = 'sure valuables'
REGULAR = 'regular'
MODES = (SURE, REGULAR)  # in the order a double press goes through them; the first is the default
RUNES = frozenset(('rune',))
GEMS = frozenset(('gema', 'gemd', 'geme', 'gemr', 'gems', 'gemt', 'gemz'))  # amethyst ... skull, every grade
CHARMS = frozenset(('scha', 'mcha', 'lcha', 'csch'))  # small, large, grand, the Crafted Sunder Charm
RING = 'ring'
RARE = RARITIES['rare']


def sure(drop: Drop) -> bool:
    """Whether the drop is one the sure mode takes: a supply (gold, a potion), or a valuable of the module text."""
    if drop.kind != VALUABLE:
        return True
    if drop.source == 'unique':
        return True
    base = item_base(drop.txt) if drop.txt else None
    kind = base['type'] if base is not None else None
    if kind in RUNES or kind in GEMS or kind in CHARMS:
        return True
    return kind == RING and drop.quality == RARE


def kept(loot: Loot, mode: str) -> Loot:
    """`loot` with only the drops `mode` takes."""
    if mode == REGULAR:
        return loot
    return replace(loot, drops=tuple(drop for drop in loot.drops if sure(drop)))


def next_mode(mode: str) -> str:
    """The mode a double press switches to."""
    return MODES[(MODES.index(mode) + 1) % len(MODES)]
