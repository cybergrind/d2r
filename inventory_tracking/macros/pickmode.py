"""The KP_6 loop's pickup mode (routes/lower-kurast-loop-plan.md phase 7), switched by a double press of KP_6.

The player, 2026-10-16: "by default only 100% valuables (rare rings, known good uniques, all runes, all gems, all
charms). and can switch for pickup regular - what do we have right now"; and "we pickup gold, we need it to repair our
staff of teleportation".

- `SURE` (the default): of what the regular pickup takes, only the sure valuables. Every rune, gem, charm and jewel
  (the player, later that day: "make sure that we still pickup all jewels"); a rare, set or unique ring or amulet
  (the player, 2026-10-17: "rare amulets - also pickup"; the read finds jewelry as a material, so a set or unique
  one is not the loot filter's `NAMED` and is taken here: a set Amulet was left at 08:10:10); a unique or set item
  the loot marks price (`source` 'unique': loot/data/uniques.json at `unique_minimum` Ist and up); and whatever the
  loot marks point at (`Drop.prized`, world.py `prized`: the worldstone shards, essences, statues, flawless and
  perfect gems, every unique and set item the loot filter shows; the player: "+ pickup worldstone shards/other
  valuable drops").
  The supplies stay in every mode: gold, and the potions the belt is short of.
  And the bases judged by their rolls off the ground, which need no identify: a white or superior base of the Void
  line (Thul-Zod-Ist, guides/warlock.html, `void_base`; the player, 2026-10-17: "good void base with +3 for
  example"), a Monarch or an elite Paladin shield (`shield_base`).
- `TRADE`: the sure valuables, and the trade goods (`identified_for`): of what the loot filter shows, a magic or rare
  item of a type that rolls skills (the class items, the Warlock's daggers and grimoires, circlets), taken to be
  identified and appraised in town and the junk sold for gold (macros/junk.py; the player, 2026-10-17: "picking items
  with +skill, identifying them, appraising, selling [bad ones] and repairing on these money"). They were in the sure
  mode while the gold paid the staff's Teleport charges; with Enigma the gold has little use (the player, 2026-10-18:
  "because we now don't need gold anymore ... move things that we're added for gold trades (to repair our staff
  charges) into separate category ... and use sure for valuable things or small things").
- `REGULAR`: today's pickup, untouched (macros/pickup.py `wanted`, `choose`).

A double press of KP_6 goes SURE, TRADE, REGULAR and round again.

A filter over the drops the regular rules found (`kept`), so no rule is written twice: the sure mode never takes what
the regular one would not. The item types are the game's own (items/metadata.py `item_base`: misc.txt's type column),
listed from the bundled metadata on 2026-10-16, not written from memory.
"""

from dataclasses import replace

from inventory_tracking.items.metadata import item_base
from inventory_tracking.loot.shown import RARITIES
from inventory_tracking.macros.world import VALUABLE, Drop, Loot


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
# The types that roll skills (the classes' items: the Amazon's bows, spears and javelins, the Sorceress's orbs, the
# Necromancer's wands and heads, the Paladin's scepters and shields, the Barbarian's helms, the Druid's pelts,
# the Assassin's claws; the Warlock's grimoires and daggers, guides/warlock.html §6) and circlets: magic or rare. The
# player, 2026-10-17: "the most gold cost is weapons and items that can give +skills (35k for good rolls)
# blades/daggers/necro/sorc, also class specific offhands can roll": gloves, boots and belts left (no skills to roll)
# The player, 13:36: "high-value trade only". Sales 11:26-13:36 on 2026-10-17 (trade.py), gold a sale: Paladin shields
# 32.5k, rare daggers 35k, claws 22.5k, magic daggers 20.2k (15), circlets 15.4k, grimoires 14.1k (11), Barbarian helms
# 13.3k (10), Druid pelts 12.4k; magic amulets 2.2k (8) and Amazon javelins 1.1k left: the Amazon's bows, spears and
# javelins and the magic amulets are no candidates now. Wands, heads, orbs, scepters: the player's "necro/sorc ...
# class specific offhands", kept untried
SKILLED = frozenset(('orb', 'wand', 'head', 'scep', 'ashd', 'phlm', 'pelt', 'h2h', 'h2h2', 'grim', 'knif', 'circ'))
# The Void line's bases (items metadata, 2026-10-17): Kriss, Blade, Cinquedeas, Stilleto, Fanged Knife, Legend Spike;
# white or superior, the others of the line hold one socket at most (the warlock pickup study, 2026-10-17)
VOID_BASES = frozenset((41, 42, 134, 135, 237, 238))
# A Void base worth its cells: exactly the 3 sockets Void needs and a Warlock staff mod buyers pay for (the player,
# 2026-10-17 18:56: "we're storing daggers with 1os ... we need good staff mod and we need 3os; we shouldn't waste
# shared stash tab"). The skills (skills metadata ids) and the least level: VOID_STAFFMODS, VOID_LEVEL
VOID_SOCKETS = 3
# Abyss and Hex: Purge (skills metadata ids; Traderie properties 1579 and 1566): of the scoped Traderie asks, fills and
# buyers (pulls of 2026-09-18 to 10-09), a white or superior 3os base with +3 Abyss asked a median 11.4 Ist (32 sellers)
# and filled at 8.2 (23); +3 Hex: Purge filled at 17.5 (7); 14 and 4 of 26 buyers want them, every other skill one or
# none; +2 at best filled at 1.0-1.4. 1os and 2os bases had no market; elite bases no premium of their own
VOID_STAFFMODS = frozenset((402, 389))
VOID_LEVEL = 3
# Or no socket and +3 Abyss: asked 11.4 Ist as the 3os did (the market study), sockets added by Larzuk's quest (the
# player, 19:40 on 2026-10-17: "0 socket +3 abyss - let's pickup them")
ABYSS = 402
# Monarchs and elite Paladin shields (items metadata classes). Scoped Traderie asks, fills and buyers of 2026-09-18 to
# 10-09 (the market study of 19:15 on 2026-10-17): a Monarch normal 4os asked 0.79 Ist (16 sellers), superior under
# 15% ED 4os 2.0 (5), superior 15% ED 4os 17.1, 0os 11.4 (Larzuk), eth 137 (4, 4, 3: thin, asks only); magic 4os 28.6
# (14), of Deflecting 103 (8). A Sacred Targe 45 all res asked 11.4 (4os, 12; fills 11.4-17.3), 40.6 (3os, 12; fills
# 34.3), eth 68.5 (fills 34.3-45.7); 40-44 all res 3/4os filled 2.0-11.4; under 40 1.0. A Sacred Rondache 45 4os 5.9,
# eth 45.7, superior 15% ED 114; 40-44 1.6
MONARCH, SACRED_TARGE, SACRED_RONDACHE = 447, 498, 499
SUPERIOR = RARITIES['hiQuality']
SUPERIOR_MOST = 15  # a superior armor's enhanced defense at most: the Monarch that sells
SHIELD_SOCKETS = 4
FULL_RESISTS, GOOD_RESISTS = 45, 40  # a Paladin shield's all-resistance roll
WHITE = frozenset((RARITIES['normal'], RARITIES['hiQuality']))


def sure(drop: Drop) -> bool:
    """Whether the drop is one the sure mode takes: a supply (gold, a potion), or a valuable of the module text; not a
    trade good (`traded`)."""
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
    """Whether the drop is one the trade mode takes: what the sure mode takes, and a trade good (the module text)."""
    if sure(drop):
        return True
    base = item_base(drop.txt) if drop.txt else None
    return candidate(drop, base['type'] if base is not None else None)


def judged_base(drop: Drop) -> bool:
    """Whether the drop is a base kept by its rolls read off the ground (`void_base`, `shield_base`), of what the loot
    filter shows."""
    return drop.source in ('shown', 'material') and (void_base(drop) or shield_base(drop))


def candidate(drop: Drop, kind: str | None) -> bool:
    """Whether the drop, of the item type `kind`, is a candidate for an identify (the module text)."""
    if drop.source != 'shown' and drop.source != 'material':
        return False
    return identified_for(kind, drop.quality) or void_base(drop) or shield_base(drop)


def void_base(drop: Drop) -> bool:
    """Whether the drop is a white or superior Void base worth keeping: VOID_SOCKETS sockets and a staff mod of
    VOID_STAFFMODS at VOID_LEVEL or more, or no socket and ABYSS at VOID_LEVEL, read off the ground (world.py
    `rolled`). Unread: not taken (a base is worth little, and one taken unread fills the stash: the player's daggers
    with one socket, 18:56 on 2026-10-17)."""
    found = drop.rolls
    if drop.quality not in WHITE or drop.txt not in VOID_BASES or found is None:
        return False
    paid = VOID_STAFFMODS if found.sockets == VOID_SOCKETS else (ABYSS,) if found.sockets == 0 else ()
    return any(skill in paid and level >= VOID_LEVEL for skill, level in found.skills)


def shield_base(drop: Drop) -> bool:
    """Whether the drop is a Monarch or an elite Paladin shield worth its cells, by its rolls read off the ground (the
    player, 19:10 on 2026-10-17: "start picking up monarchs (for 4os deflecting) and sacred targes (check what are
    expensive ones)"; the market study's rule, SHIELD_* below). Unread: not taken."""
    found = drop.rolls
    if found is None:
        return False
    if drop.txt == MONARCH:
        if drop.quality == MAGIC:
            return found.sockets == SHIELD_SOCKETS  # identified at Cain, then appraised: of Deflecting or not
        return drop.quality == SUPERIOR and found.defense >= SUPERIOR_MOST and found.sockets in (0, SHIELD_SOCKETS)
    if drop.quality not in WHITE:
        return False  # a magic Paladin shield is a candidate for an identify as it was (`identified_for`)
    if drop.txt == SACRED_TARGE:
        return found.resists >= FULL_RESISTS or (found.resists >= GOOD_RESISTS and found.sockets >= 3)
    if drop.txt == SACRED_RONDACHE:
        return found.resists >= FULL_RESISTS and (
            found.sockets == SHIELD_SOCKETS or found.ethereal or drop.quality == SUPERIOR
        )
    return False


def sellable(kind: str | None, quality: int, txt: int | None = None) -> bool:
    """Whether an item of type `kind`, `quality` and class `txt` may be the loop's junk once identified and appraised
    `vendor` (macros/junk.py): what it takes only to identify (`identified_for`), magic or rare charms (the player,
    2026-10-17 11:25: "you can sell identified junk charms"), and a white or superior Void base (the player, 17:45:
    "we're storing every 3os dagger, while in reality we need something that is really good for void": the appraisal
    prices its sockets and Warlock skills, pricing/triage `void-three-socket`), and magic or rare jewels, rings and
    amulets (the player, 19:06: "actually, we can sell trash jewels/rings/amus"); and a set, unique or crafted item
    the appraisal calls junk (the player, 11:10 on 2026-10-18: "we should sell junk rings and other junk items;
    imporant!: do not sell own equipment or valuable items"), but never a charm of them: the Sunders, Gheed's, Annihilus
    and the Torch are the loop's quarry whatever a price says. Never a rune or gem; nor the Crafted Sunder Charm."""
    return (
        identified_for(kind, quality)
        or (quality in (SET, UNIQUE, CRAFTED) and kind is not None and kind not in CHARMS)
        or (quality in (MAGIC, RARE) and kind in (*CHARMS, *JEWELS, RING, AMULET) and kind != 'csch')
        or (quality in WHITE and txt in VOID_BASES)
        or (quality == MAGIC and txt == MONARCH)
    )


def identified_for(kind: str | None, quality: int) -> bool:
    """Whether an item of type `kind` and `quality` is one the loop takes only to identify it: the only items its
    junk may be besides charms (`sellable`). Never a rune, gem, jewel, ring, or a rare, set or unique amulet: the sure
    valuables are kept whatever the appraisal says (the player: "we shouldn't sell our own equipment or valuable
    items")."""
    return quality in (MAGIC, RARE) and kind in SKILLED


def is_candidate(drop: Drop) -> bool:
    """Whether the drop is a candidate (`candidate`) and nothing more: a valuable the loop takes only to identify it.
    The guards that keep a game for a valuable on the ground (runner.py `_valuable_left`, macros/sightings.py) are not
    for these: one left behind costs a game nothing."""
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
