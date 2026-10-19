"""The KP_6 loop's pickup mode, cycled by a double press of KP_6: SURE, TRADE, REGULAR (rulings and market evidence:
history/pickmode.md).

- `SURE` (default): only the sure valuables of what the regular pickup takes: every rune, gem, charm and jewel; a
  rare, set or unique ring or amulet; a unique or set item the loot marks price; whatever the loot marks point at
  (`Drop.prized`); bases judged by their rolls off the ground (`void_base`, `shield_base`). Supplies (gold, potions
  the belt is short of) in every mode.
- `TRADE`: the sure valuables and the trade goods (`identified_for`): magic or rare items of types that roll skills,
  identified, appraised and the junk sold in town (macros/junk.py).
- `REGULAR`: the regular pickup (macros/pickup.py `wanted`, `choose`).

A filter over the drops the regular rules found (`kept`): no mode takes what the regular one would not. Item types
are the game's (items/metadata.py `item_base`), not written from memory.
"""

from dataclasses import replace

from inventory_tracking.game.records import VALUABLE, Drop, Loot
from inventory_tracking.items.metadata import item_base
from inventory_tracking.loot.shown import RARITIES


__all__ = [
    'MODES',
    'REGULAR',
    'SURE',
    'TRADE',
    'WHITE',
    'candidate',
    'identified_for',
    'is_candidate',
    'kept',
    'next_mode',
    'sellable',
    'shield_base',
    'sure',
    'traded',
    'void_base',
]

SURE = 'sure valuables'
TRADE = 'sure and trade goods'
REGULAR = 'regular'
MODES = (SURE, TRADE, REGULAR)  # in the order a double press goes through them; the first is the default
RUNES = frozenset(('rune',))
GEMS = frozenset(('gema', 'gemd', 'geme', 'gemr', 'gems', 'gemt', 'gemz'))  # amethyst ... skull, every grade
CHARMS = frozenset(('scha', 'mcha', 'lcha', 'csch'))  # small, large, grand, the Crafted Sunder Charm
JEWELS = frozenset(('jewl', 'cjwl'))  # Jewel, Colossal Jewel
RING = 'ring'
AMULET = 'amul'
RARE = RARITIES['rare']
JEWELRY_QUALITIES = frozenset((RARE, RARITIES['set'], RARITIES['unique']))
MAGIC = RARITIES['magic']
SET, UNIQUE, CRAFTED = RARITIES['set'], RARITIES['unique'], 8  # ItemData quality (8: crafted)
# Types that roll skills (class items, Warlock daggers and grimoires, circlets), by the gold a sale fetched
# (2026-10-17, history/pickmode.md); the Amazon's and magic amulets dropped ("high-value trade only", the player)
SKILLED = frozenset(('orb', 'wand', 'head', 'scep', 'ashd', 'phlm', 'pelt', 'h2h', 'h2h2', 'grim', 'knif', 'circ'))
# The Void line's bases that take 3 sockets (items metadata, 2026-10-17): Kriss, Blade, Cinquedeas, Stilleto, Fanged
# Knife, Legend Spike
VOID_BASES = frozenset((41, 42, 134, 135, 237, 238))
# A Void base worth its cells: exactly 3 sockets and a staff mod buyers pay for ("we need good staff mod and we need
# 3os; we shouldn't waste shared stash tab", the player, 2026-10-17)
VOID_SOCKETS = 3
# Abyss and Hex: Purge (skills metadata ids): +3 filled 8.2 and 17.5 Ist, +2 at best 1.0-1.4 (Traderie, 2026-09-18 to
# 10-09; history/pickmode.md)
VOID_STAFFMODS = frozenset((402, 389))
VOID_LEVEL = 3
# Or no socket and +3 Abyss, socketed by Larzuk ("0 socket +3 abyss - let's pickup them", the player, 2026-10-17)
ABYSS = 402
# Monarchs and elite Paladin shields (items metadata classes); the rules follow the market study of 2026-10-17
# (history/pickmode.md)
MONARCH, SACRED_TARGE, SACRED_RONDACHE = 447, 498, 499
SUPERIOR = RARITIES['hiQuality']
SUPERIOR_MOST = 15  # a superior armor's enhanced defense at most: the Monarch that sells
SHIELD_SOCKETS = 4
FULL_RESISTS, GOOD_RESISTS = 45, 40  # a Paladin shield's all-resistance roll
WHITE = frozenset((RARITIES['normal'], RARITIES['hiQuality']))


def sure(drop: Drop) -> bool:
    """Whether the sure mode takes the drop: a supply, or a sure valuable (the module text)."""
    if drop.kind != VALUABLE:
        return True
    if drop.source == 'unique' or drop.prized:
        return True
    base = item_base(drop.txt) if drop.txt else None
    kind = base['type'] if base is not None else None
    if kind in RUNES or kind in GEMS or kind in CHARMS or kind in JEWELS:
        return True
    if kind in (RING, AMULET) and drop.quality in JEWELRY_QUALITIES:
        return True
    return judged_base(drop)


def traded(drop: Drop) -> bool:
    """Whether the trade mode takes the drop: what the sure mode takes, and a trade good."""
    if sure(drop):
        return True
    base = item_base(drop.txt) if drop.txt else None
    return candidate(drop, base['type'] if base is not None else None)


def judged_base(drop: Drop) -> bool:
    """Whether the drop is a shown base kept by its rolls read off the ground."""
    return drop.source in ('shown', 'material') and (void_base(drop) or shield_base(drop))


def candidate(drop: Drop, kind: str | None) -> bool:
    """Whether the drop, of item type `kind`, is a candidate for an identify."""
    if drop.source != 'shown' and drop.source != 'material':
        return False
    return identified_for(kind, drop.quality) or void_base(drop) or shield_base(drop)


def void_base(drop: Drop) -> bool:
    """Whether the drop is a white or superior Void base worth keeping: VOID_SOCKETS sockets and a VOID_STAFFMODS
    skill at VOID_LEVEL+, or no socket and ABYSS at VOID_LEVEL+. Unread rolls: not taken (unread bases filled the
    stash, 2026-10-17)."""
    found = drop.rolls
    if drop.quality not in WHITE or drop.txt not in VOID_BASES or found is None:
        return False
    paid = VOID_STAFFMODS if found.sockets == VOID_SOCKETS else (ABYSS,) if found.sockets == 0 else ()
    return any(skill in paid and level >= VOID_LEVEL for skill, level in found.skills)


def shield_base(drop: Drop) -> bool:
    """Whether the drop is a Monarch or an elite Paladin shield worth its cells, by its rolls ("start picking up
    monarchs (for 4os deflecting) and sacred targes", the player, 2026-10-17). Unread: not taken."""
    found = drop.rolls
    if found is None:
        return False
    if drop.txt == MONARCH:
        if drop.quality == MAGIC:
            return found.sockets == SHIELD_SOCKETS  # identified, then appraised: of Deflecting or not
        return drop.quality == SUPERIOR and found.defense >= SUPERIOR_MOST and found.sockets in (0, SHIELD_SOCKETS)
    if drop.quality not in WHITE:
        return False  # a magic Paladin shield is an identify candidate (`identified_for`)
    if drop.txt == SACRED_TARGE:
        return found.resists >= FULL_RESISTS or (found.resists >= GOOD_RESISTS and found.sockets >= 3)
    if drop.txt == SACRED_RONDACHE:
        return found.resists >= FULL_RESISTS and (
            found.sockets == SHIELD_SOCKETS or found.ethereal or drop.quality == SUPERIOR
        )
    return False


def sellable(kind: str | None, quality: int, txt: int | None = None) -> bool:
    """Whether an item of type `kind`, `quality` and class `txt` may be the loop's junk once appraised `vendor`: the
    identify candidates, magic or rare charms, jewels, rings and amulets, white or superior Void bases, magic Monarchs,
    and set, unique or crafted items except charms (the Sunders, Gheed's, Annihilus and the Torch are the loop's quarry
    whatever a price says). Never a rune, gem or the Crafted Sunder Charm. Rulings: history/pickmode.md."""
    return (
        identified_for(kind, quality)
        or (quality in (SET, UNIQUE, CRAFTED) and kind is not None and kind not in CHARMS)
        or (quality in (MAGIC, RARE) and kind in (*CHARMS, *JEWELS, RING, AMULET) and kind != 'csch')
        or (quality in WHITE and txt in VOID_BASES)
        or (quality == MAGIC and txt == MONARCH)
    )


def identified_for(kind: str | None, quality: int) -> bool:
    """Whether the loop takes an item of type `kind` and `quality` only to identify it. Never a sure valuable: those
    are kept whatever the appraisal says."""
    return quality in (MAGIC, RARE) and kind in SKILLED


def is_candidate(drop: Drop) -> bool:
    """Whether the drop is only an identify candidate. The guards that keep a game for a valuable on the ground
    (runner.py `_valuable_left`) skip these: one left behind costs nothing."""
    base = item_base(drop.txt) if drop.txt else None
    return drop.kind == VALUABLE and not drop.prized and candidate(drop, base['type'] if base is not None else None)


def kept(loot: Loot, mode: str) -> Loot:
    """`loot` with only the drops `mode` takes."""
    if mode == REGULAR:
        return loot
    takes = traded if mode == TRADE else sure
    return replace(loot, drops=tuple(drop for drop in loot.drops if takes(drop)))


def next_mode(mode: str) -> str:
    """The mode a double press switches to."""
    return MODES[(MODES.index(mode) + 1) % len(MODES)]
