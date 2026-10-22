"""The pickup level of every loop and activity, GOOD or MOST, switched by a KP_6 double press (the player, 2026-10-19:
"I want to enable the same drop pickup rules as for other loops - by default we pickup sure items"; the trade goods'
level dropped the same evening; rulings and market evidence: history/pickmode.md).

- `SURE` (GOOD on the HUD, the default): only the sure valuables of what the regular pickup takes: every rune, gem,
  charm and jewel; a rare, set or unique ring or amulet; a unique or set item the loot marks price; whatever the loot
  marks point at (`Drop.prized`); bases judged by their rolls off the ground (`void_base`, `shield_base`). Supplies
  (gold, potions the belt is short of) in every mode.
- `MOST`: the regular pickup (macros/pickup.py `wanted`, `choose`): what KP_1 took before 2026-10-19.

A filter over the drops the regular rules found (`kept`): no mode takes what the regular one would not. Item types
are the game's (items/metadata.py `item_base`), not written from memory.

Since 2026-10-20 (the player, ~11:55: "bases or blue/rare items might take much place (like spears, matron bow) -- we
want to check them and drop in the middle of the run"; ~12:00 "start all three"):
- M5 (loot/ground_judge.py BASES): a white or superior base is also taken by its ground read and the wants rows
  (`ground_base`: eth 4os merc polearms and armor, Superior 15 ED runeword and market bases); a must-have row's
  (the merc BiS bases) is `prized` (no game left with it, a press stops for it). Today's dagger and shield rules stay.
- The bases over the cell cap the look now reads (macros/pickup.py `shown_rules`) are kept, in every level, only
  when the ground read picks them (white) or the field identify takes them (magic, rare: loot/api.py G15).
- With the loop on, the MOST level's magic and rare items are remembered for the field identify too (loot/api.py
  `Field.pick`), so a bad one is dropped in the field, not carried to town.
- Since ~14:28 (the player: "we must redesign our routins to actually have space for mid-run identifying big items"):
  a big field item is taken into the free block though no Grand Charm's room is left after it, one at a time, with
  the Tome's charges (`kept`'s `tome`) and no sure valuable losing its room (loot/api.py FIELD_AT_ONCE).
"""

from collections.abc import Callable
from dataclasses import replace

from inventory_tracking.common import LOG
from inventory_tracking.game.records import VALUABLE, Drop, Loot
from inventory_tracking.items.metadata import item_base
from inventory_tracking.loot import api as field_api, ground_judge, value as loot_value
from inventory_tracking.loot.api import FIELD, oversize
from inventory_tracking.loot.facts import from_drop
from inventory_tracking.loot.ground_judge import GroundVerdict
from inventory_tracking.loot.shown import RARITIES


__all__ = [
    'MODES',
    'MOST',
    'SURE',
    'WHITE',
    'candidate',
    'ground_base',
    'identified_for',
    'is_candidate',
    'kept',
    'next_mode',
    'sellable',
    'shield_base',
    'sure',
    'void_base',
]

SURE = 'good'
MOST = 'most'
MODES = (SURE, MOST)  # in the order KP_5 goes through them; the first is the default
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
# The staff mods a 3os Void base is kept for, at +3: the Warlock's useful skills (skills.json ids, checked in
# third-parties/d2data/json/skills.json 2026-10-20): Abyss 402 and Hex: Purge 389, +3 filled 8.2 and 17.5 Ist, +2 at
# best 1.0-1.4 (Traderie, 2026-09-18 to 10-09; history/pickmode.md); Apocalypse 401, +3 asks ~5 (n24; loot/design.md
# §4.2 G8). The player, 2026-10-20 08:42: "+3os daggers with +3 apocalypse"; Q9 as recommended: "only +3 Abyss /
# Hex: Purge / Apocalypse"
VOID_STAFFMODS = frozenset((402, 389, 401))
VOID_LEVEL = 3
# Or no socket and +3 of any of them, socketed by Larzuk or the cube ("0 socket +3 abyss - let's pickup them", the
# player, 2026-10-17; "add 0os +3 apocalypse too", 2026-10-22)
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


def judged_base(drop: Drop) -> bool:
    """Whether the drop is a shown base kept by its rolls read off the ground."""
    if drop.source not in ('shown', 'material'):
        return False
    if void_base(drop) or shield_base(drop):
        return True
    verdict = ground_base(drop)
    return verdict is not None and verdict.pick


def ground_base(drop: Drop) -> GroundVerdict | None:
    """M5: the ground read's verdict on a shown white or superior base the wants rows judge (loot/ground_judge.py
    `base_verdict`), None for any other drop, with its rolls unread, or with the switch off."""
    if drop.kind != VALUABLE or drop.quality not in WHITE or drop.source not in ('shown', 'material'):
        return None
    if drop.rolls is None or not ground_judge.BASES:
        return None
    try:
        return ground_judge.base_verdict(from_drop(drop), owned=loot_value.owned_bases)  # the Spirit Monarch cap
    except Exception as error:  # the wants unreadable (another edit under way): today's rules alone
        LOG.debug('Macro: pickup: no ground verdict on %s: %s', drop.label, error)
        return None


def candidate(drop: Drop, kind: str | None) -> bool:
    """Whether the drop, of item type `kind`, is a candidate for an identify (or a base no game is kept for: a
    must-have base is `prized` instead, `kept`)."""
    if drop.source != 'shown' and drop.source != 'material':
        return False
    if identified_for(kind, drop.quality) or void_base(drop) or shield_base(drop):
        return True
    verdict = ground_base(drop)
    return verdict is not None and verdict.pick and not verdict.must_have


def void_base(drop: Drop) -> bool:
    """Whether the drop is a white or superior Void base worth keeping: VOID_SOCKETS sockets or none, and a
    VOID_STAFFMODS skill at VOID_LEVEL+. Unread rolls: not taken (unread bases filled the stash, 2026-10-17)."""
    found = drop.rolls
    if drop.quality not in WHITE or drop.txt not in VOID_BASES or found is None:
        return False
    if found.sockets not in (0, VOID_SOCKETS):
        return False
    return any(skill in VOID_STAFFMODS and level >= VOID_LEVEL for skill, level in found.skills)


def shield_base(drop: Drop) -> bool:
    """Whether the drop is a Monarch or an elite Paladin shield worth its cells, by its rolls ("start picking up
    monarchs (for 4os deflecting) and sacred targes", the player, 2026-10-17). Unread: not taken."""
    found = drop.rolls
    if found is None:
        return False
    if drop.txt == MONARCH:
        if drop.quality == MAGIC:
            return found.sockets == SHIELD_SOCKETS  # identified, then appraised: of Deflecting or not
        # ED unread (None: its +0xD0 chain was not read whole) is not taken
        ed = found.defense or 0
        return drop.quality == SUPERIOR and ed >= SUPERIOR_MOST and found.sockets in (0, SHIELD_SOCKETS)
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
    identify candidates and any other magic or rare item (a magic Matriarchal Javelin the loot filter showed was
    stashed, not sold, at 21:55:27 on 2026-10-19: "trash item ... forgot to ... sell"), white or superior Void bases,
    and set, unique or crafted items except charms (the Sunders, Gheed's, Annihilus and the Torch are the loop's quarry
    whatever a price says). Never a rune, gem or the Crafted Sunder Charm. Rulings: history/pickmode.md."""
    return (
        identified_for(kind, quality)
        or (quality in (SET, UNIQUE, CRAFTED) and kind is not None and kind not in CHARMS)
        or (quality in (MAGIC, RARE) and kind is not None and kind not in (*RUNES, *GEMS, 'csch'))
        or (quality in WHITE and txt in VOID_BASES)
    )


def identified_for(kind: str | None, quality: int) -> bool:
    """Whether the loop takes an item of type `kind` and `quality` only to identify it. Never a sure valuable: those
    are kept whatever the appraisal says."""
    return quality in (MAGIC, RARE) and kind in SKILLED


def is_candidate(drop: Drop) -> bool:
    """Whether the drop is only an identify candidate. The guards that keep a game for a valuable on the ground
    (runner.py `_valuable_left`) skip these: one left behind costs nothing. With the loop on, a drop picked for the
    field identify too (loot/api.py `Field.takes`, M4: a magic Monarch is no must-have, design.md §4.2 G6)."""
    base = item_base(drop.txt) if drop.txt else None
    if drop.kind != VALUABLE or drop.prized:
        return False
    return candidate(drop, base['type'] if base is not None else None) or FIELD.takes(drop) is not None


def kept(loot: Loot, mode: str, tome: Callable[[], int | None] | None = None) -> Loot:
    """`loot` with only the drops `mode` takes; `tome()` the Tome of Identify's charges, read only for a big field item
    taken into the free block (loot/api.py `Field.pick`, FIELD_AT_ONCE)."""
    try:  # the loot design's shadow (loot/design.md §7 M1): the new ground verdicts beside this mode's; log only
        from inventory_tracking.loot.shadow import ground as shadow

        shadow(loot, lambda drop: mode == MOST or sure(drop))
    except Exception as error:  # never into the look
        LOG.debug('Macro: loot: shadow: ground not logged: %s', error)
    drops = tuple(found for drop in loot.drops if (found := _kept(drop, mode, loot, tome)) is not None)
    return replace(loot, drops=drops)


def _kept(drop: Drop, mode: str, loot: Loot, tome: Callable[[], int | None] | None = None) -> Drop | None:
    """`drop` as `mode` takes it (`_taken`); a big set or unique one taken is remembered for the field check (G18,
    loot/api.py `Field.note`; the player, 2026-10-20 ~13:28: "identify a big items in the middle of the run"): what
    is taken does not change."""
    found = _taken(drop, mode, loot, tome)
    if found is not None:
        FIELD.note(found, loot.game)
        FIELD.park(found, loot.game)  # stash-bound: into the cube at the next quiet look (loot/api.py CUBE_AT_PICKUP)
    return found


def _taken(drop: Drop, mode: str, loot: Loot, tome: Callable[[], int | None] | None = None) -> Drop | None:
    """`drop` as `mode` takes it (a must-have base `prized`), None when it does not (the module text)."""
    based = ground_base(drop)
    if based is not None and based.pick and based.must_have and not drop.prized:
        drop = replace(drop, prized=True)  # the merc BiS bases: no game is left with one on the ground
    if drop.kind == VALUABLE and drop.source == 'shown' and oversize(drop):
        # Over the cell cap only what the ground read or the field identify judges, in every level
        if based is not None:
            return drop if based.pick else None
        return drop if _field_pick(drop, loot, tome) else None
    if mode == MOST:
        if field_api.FIELD_BIG and not sure(drop):
            _field_pick(drop, loot, tome)  # remembered: identified in the field, the bad ones dropped there
        return drop
    # M4 (the player, 2026-10-20: "just get it, identify with scroll, and drop if it is bad"): the loop takes the
    # classes of the field identify too, each remembered for its routine (loot/api.py `Field.pick`)
    return drop if sure(drop) or _field_pick(drop, loot, tome) else None


def _field_pick(drop: Drop, loot: Loot, tome: Callable[[], int | None] | None) -> bool:
    """`Field.pick` with the facts a big item is taken into the free block by (loot/api.py FIELD_AT_ONCE; the player,
    2026-10-20 ~14:28: "we must redesign our routins to actually have space for mid-run identifying big items"): the
    units carried, the look's other sure valuables (asked only then) and the Tome's charges."""

    def waiting() -> list[Drop]:
        return [d for d in loot.drops if d.unit_id != drop.unit_id and d.kind == VALUABLE and sure(d)]

    return FIELD.pick(drop, loot.game, loot.room, carried=loot.carried, waiting=waiting, tome=tome)


def next_mode(mode: str) -> str:
    """The level a KP_6 double press switches to."""
    return MODES[(MODES.index(mode) + 1) % len(MODES)]
