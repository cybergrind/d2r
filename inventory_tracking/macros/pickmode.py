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
from inventory_tracking.loot import api as field_api, assess, base_floor, ground_judge, value as loot_value
from inventory_tracking.loot.api import FIELD, oversize
from inventory_tracking.loot.facts import from_drop
from inventory_tracking.loot.ground_judge import BASE_CLASSES, GroundVerdict
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
    """Whether the sure mode takes the drop: a supply, or a sure valuable (the module text); legacy (`good`)."""
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
    """Legacy until ASSESS_GROUND is proven (`identify_only`). Whether the drop is only an identify candidate. The
    guards that keep a game for a valuable on the ground (runner.py `_valuable_left`) skip these: one left behind costs
    nothing. With the loop on, a drop picked for the field identify too (loot/api.py `Field.takes`, M4: a magic
    Monarch is no must-have, design.md §4.2 G6)."""
    base = item_base(drop.txt) if drop.txt else None
    if drop.kind != VALUABLE or drop.prized:
        return False
    return candidate(drop, base['type'] if base is not None else None) or FIELD.takes(drop) is not None


def kept(loot: Loot, mode: str, tome: Callable[[], int | None] | None = None) -> Loot:
    """`loot` with only the drops `mode` takes; `tome()` the Tome of Identify's charges, read only for a big field item
    taken into the free block (loot/api.py `Field.pick`, FIELD_AT_ONCE). Legacy until ASSESS_GROUND is proven
    (`taken`)."""
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


def junk_base(drop: Drop, based: GroundVerdict | None = None) -> str | None:
    """Why the shown white or superior `drop` is left on the ground, in every level (loot/base_floor.py BASE_FLOOR,
    2026-10-23, the player: "we're wasting our inventory space with flails"), None when it is not: the offline KB
    prices its facts read clearly under the floor. A base the wants rows pick (`based`, the ground read's verdict)
    never is; one whose staff mods, tabs or resistances those rows read and left is priced by its base alone; any
    doubt keeps it."""
    if based is not None and based.pick:
        return None
    judged = based is not None and drop.rolls is not None and based.reason != 'its rolls are not read'
    try:
        return base_floor.drop_junk(drop, judged=judged)
    except Exception as error:  # the table or the metadata unreadable: taken as before
        LOG.debug('Macro: pickup: no base floor on %s: %s', drop.label, error)
        return None


# The plain bases by the allowlist: loot/base_floor.py PLAIN_BY_RULES (moved there 2026-10-23, phase 2A; its text has
# the rulings), read here by the legacy `plain_base` and by loot/assess.py GROUND
PLAIN_CATEGORIES = frozenset(('weapons', 'armor'))
NEVER_LEFT_CODES = frozenset(('leg',))  # Wirt's Leg (keep.py NEVER_SOLD_CODES)
PLAIN_SOURCES = frozenset(('shown', 'material'))  # the filter's reasons a white base is on the ground list


def _allowlisted(drop: Drop) -> bool:
    """Whether a must-have row's base is on the allowlist too (PLAIN_BY_RULES; the coordinator, 2026-10-23: "every
    base must worth 4+ist at least" holds for the must-have rows: the eth 4os Dusk Shroud at ~0.79 Ist is left)."""
    if not base_floor.PLAIN_BY_RULES:
        return True
    try:
        return base_floor.allowed(from_drop(drop)) is not None
    except Exception as error:  # the allowlist unreadable: not prized (left by `plain_base`)
        LOG.debug('Macro: pickup: no allowlist for %s: %s', drop.label, error)
        return False


def plain_base(
    drop: Drop, based: GroundVerdict | None = None, game: object = None, *, remember: bool = True
) -> tuple[bool, str] | None:
    """PLAIN_BY_RULES: (taken, why) for a shown white or grey weapon or armor (the filter's 'shown' or 'material': a
    3os +3 Apocalypse dagger read as material went the old path, the verifier 2026-10-23); None for any other drop, a
    prized one (the usual path), or with the switch off. `game`: the Loot's, the taken base remembered under it
    (`remember`: the shadow's old decision remembers none)."""
    if not base_floor.PLAIN_BY_RULES or drop.prized or drop.quality not in WHITE or drop.source not in PLAIN_SOURCES:
        return None
    base = item_base(drop.txt) if drop.txt else None
    if base is None or base.get('category') not in PLAIN_CATEGORIES or base.get('code') in NEVER_LEFT_CODES:
        return None
    if drop.rolls is None:
        return False, 'its rolls unread: on no allowlist entry ("unread bases filled the stash", 2026-10-17)'
    try:
        why = base_floor.allowed(from_drop(drop))
        if why is not None:
            if remember:
                base_floor.remember(drop.unit_id, why, game)
            return True, why
        junk = base_floor.drop_junk(drop, judged=True)
    except Exception as error:  # the allowlist or the metadata unreadable: left (no base is worth a guess)
        LOG.info('Macro: pickup: no allowlist for %s (%s): left', drop.label, error)
        return False, 'the allowlist unreadable'
    return False, junk or 'on no allowlist entry (loot/data/base-pickups.json, 4+ Ist)'


# The junk bases said already (`_left_junk`), by game and unit: one line each
JUNK_SAID: set[tuple[object, int]] = set()
JUNK_SAID_MOST = 2000


def _left_junk(drop: Drop, game: object, why: str) -> None:
    from inventory_tracking.game.decode import rolls as census_rolls  # here: the module's lines are cited (build_wants)

    said = (game, drop.unit_id)
    if said in JUNK_SAID:
        return
    if len(JUNK_SAID) > JUNK_SAID_MOST:
        JUNK_SAID.clear()
    JUNK_SAID.add(said)
    LOG.info('Macro: pickup: %s%s left on the ground: %s (loot/base_floor.py BASE_FLOOR)', drop.label,
             census_rolls(drop), why)  # fmt: skip


def _taken(drop: Drop, mode: str, loot: Loot, tome: Callable[[], int | None] | None = None) -> Drop | None:
    """`drop` as `mode` takes it (a must-have base `prized`), None when it does not (the module text)."""
    base_floor.seen(loot.game)  # the town's game for the allowlisted bases taken (keep.py K8 guard)
    based = ground_base(drop)
    if based is not None and based.pick and based.must_have and not drop.prized and _allowlisted(drop):
        drop = replace(drop, prized=True)  # the merc BiS bases: no game is left with one on the ground
    if drop.kind == VALUABLE and (why := junk_base(drop, based)) is not None:
        _left_junk(drop, loot.game, why)
        return None
    if drop.kind == VALUABLE and (plain := plain_base(drop, based, loot.game)) is not None:
        taken, why = plain
        if not taken:
            _left_junk(drop, loot.game, why)
            return None
        return drop  # on the allowlist: taken in every level and over the cell cap
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


def _field_pick(drop: Drop, loot: Loot, tome: Callable[[], int | None] | None, klass: str | None = None) -> bool:
    """`Field.pick` with the facts a big item is taken into the free block by (loot/api.py FIELD_AT_ONCE; the player,
    2026-10-20 ~14:28: "we must redesign our routins to actually have space for mid-run identifying big items"): the
    units carried, the look's other sure valuables (asked only then) and the Tome's charges; `klass` the entry point's
    field class (ASSESS_GROUND), else the field's own (`Field.takes`). The squeeze's sure valuables are the entry
    point's `good` (2026-10-23, the coordinator's ruling on the player's "one place that decides pickups/value"): an
    allowlisted base keeps its room, a base the allowlist leaves no longer holds any; `sure` with ASSESS_GROUND off."""

    def waiting() -> list[Drop]:
        return [d for d in loot.drops if d.unit_id != drop.unit_id and d.kind == VALUABLE and good(d)]

    return FIELD.pick(drop, loot.game, loot.room, carried=loot.carried, waiting=waiting, tome=tome, klass=klass)


# -- the entry point (ASSESS_GROUND, 2026-10-23) -------------------------------------------------------------------

# Since 2026-10-23 (the player: "go ahead. I want to have one place that decides pickups/value"): what each level takes
# is the one entry point's GROUND verdict (loot/assess.py, loot/design.md §10): `taken` (the level's filter: GOOD = the
# entry point's PICK, its field picks through the field's gate; MOST = the regular pickup, D9), `good` (the GOOD
# level's sure valuables) and `identify_only` (the guard's identify candidates, D10, the caller's rule over the
# verdict). `kept`, `sure`, `is_candidate` and the base rules they call are today's, legacy until ASSESS_GROUND is
# proven; the old decision is logged beside the new one where they differ (`_shadow`). Offline before the switch:
# tests/inventory_tracking/macros/test_pickmode_assess.py (the rca/2026-10-23/scripts/assess_ground.py cases, every
# allowlist entry, the acceptance table, test_pickmode's bases; GOOD and MOST, the loop on and off) and test_pickmode.py
# both ways, 0 differ. False: today's `kept`
ASSESS_GROUND = True


def assessed(drop: Drop) -> assess.Assessment:
    """The entry point's GROUND verdict on the valuable `drop` (loot/assess.py): the owned bases counted for a row's cap
    (loot/value.py `owned_bases`), the filter's shown drop for the size classes (`Look.shown`); the carry-one classes
    had already are out of the look (game/memory.py `had_already`)."""
    shown = frozenset((drop.unit_id,)) if drop.source == 'shown' else frozenset()
    return assess.Assessor(assess.NO_PRICES, counted=loot_value.owned_bases).assess(
        from_drop(drop), assess.Site.GROUND, assess.Look(shown=shown)
    )


def _promoted(drop: Drop, found: assess.Assessment) -> bool:
    """Whether the entry point makes the plain base `drop` a must-have (the merc BiS bases on the allowlist): `prized`
    in the look, no game left with it, a press stops for it (as `_taken` did)."""
    verdict = found.ground
    picked = found.plain and found.outcome == assess.Outcome.PICK
    return picked and verdict is not None and verdict.must_have and not drop.prized


def good(drop: Drop) -> bool:
    """Whether the GOOD level takes `drop` whatever the field's gate: a supply, or the entry point's sure pick
    (ASSESS_GROUND), else `sure`."""
    if not ASSESS_GROUND:
        return sure(drop)
    if drop.kind != VALUABLE:
        return True
    try:
        return assessed(drop).sure
    except Exception as error:  # the wants or the allowlist unreadable (another edit under way): today's rule
        LOG.info("Macro: pickup: no assessment of %s (%s): today's rules", drop.label, error)
        return sure(drop)


def identify_only(drop: Drop) -> bool:
    """Whether the drop is only an identify candidate: the guards that keep a game for a valuable on the ground skip it
    (lootpolicy.py; one left behind costs nothing). D10, the caller's rule over the entry point's verdict
    (ASSESS_GROUND; else `is_candidate`): not a must-have; the kinds taken only to identify (`identified_for`), a Void
    or shield base by its rolls (`void_base`, `shield_base`), a base a wants row picks that is no must-have; with the
    loop on, a drop of a field class (`Assessment.field` behind the field's gate). An allowlisted base no row picks
    holds the game (the 119.9 Ist War Pike)."""
    if not ASSESS_GROUND:
        return is_candidate(drop)
    if drop.kind != VALUABLE or drop.prized:
        return False
    try:
        found = assessed(drop)
    except Exception as error:  # the wants or the allowlist unreadable: today's rule
        LOG.info("Macro: pickup: no assessment of %s (%s): today's rules", drop.label, error)
        return is_candidate(drop)
    if _promoted(drop, found):
        return False
    if drop.source in PLAIN_SOURCES:
        base = item_base(drop.txt) if drop.txt else None
        if identified_for(base['type'] if base is not None else None, drop.quality):
            return True
        if void_base(drop) or shield_base(drop):
            return True
        verdict = found.ground
        if found.outcome == assess.Outcome.PICK and verdict is not None and verdict.klass in BASE_CLASSES:
            return not verdict.must_have
    return found.field is not None and FIELD.gate(drop)


def taken(loot: Loot, mode: str, tome: Callable[[], int | None] | None = None) -> Loot:
    """`loot` with only the drops the pickup level `mode` takes (`tome()`: the Tome's charges, for a big field item
    into the free block): the entry point's GROUND verdict (ASSESS_GROUND), else `kept`. A big set or unique drop taken
    is remembered for the field check (G18, loot/api.py `Field.note`), a stash-bound one for the cube (`Field.park`)."""
    if not ASSESS_GROUND:
        return kept(loot, mode, tome)
    base_floor.seen(loot.game)  # the town's game for the allowlisted bases taken (keep.py K8 guard)
    drops = []
    for drop in loot.drops:
        found = _assessed_taken(drop, mode, loot, tome)
        if found is not None:
            FIELD.note(found, loot.game)
            FIELD.park(found, loot.game)
            drops.append(found)
    return replace(loot, drops=tuple(drops))


def _assessed_taken(drop: Drop, mode: str, loot: Loot, tome: Callable[[], int | None] | None) -> Drop | None:
    """`drop` as `mode` takes it by the entry point (a must-have base `prized`), None when it does not: a plain base by
    the allowlist in every level; over the cell cap only a sure pick or the field's; MOST all else (D9, its field items
    remembered); GOOD the sure picks and the field's through its gate (`Field.pick`: the loop on, room)."""
    if drop.kind != VALUABLE:
        return drop  # a supply: the belt and gold rules
    try:
        found = assessed(drop)
    except Exception as error:  # the wants or the allowlist unreadable (another edit under way): today's rules
        LOG.info("Macro: pickup: no assessment of %s (%s): today's rules", drop.label, error)
        return _taken(drop, mode, loot, tome)
    _shadow(drop, mode, loot, found)
    promoted = _promoted(drop, found)
    if promoted:
        drop = replace(drop, prized=True)  # the merc BiS bases: no game is left with one on the ground
    why = found.ground.reason if found.ground is not None else found.why
    if found.plain:
        if found.outcome != assess.Outcome.PICK:
            _left_junk(drop, loot.game, why)
            return None
        if not promoted:  # as `_taken`: a must-have went the prized path, not remembered (keep.py K3 keeps its row)
            base_floor.remember(drop.unit_id, why, loot.game)
        return drop  # on the allowlist: taken in every level and over the cell cap

    def fielded() -> bool:
        return found.for_field and found.field is not None and _field_pick(drop, loot, tome, found.field)

    if drop.source == 'shown' and oversize(drop):
        return drop if found.sure or fielded() else None  # over the cell cap: what the entry point or the field takes
    if mode == MOST:
        if field_api.FIELD_BIG and not found.sure and found.field is not None:
            _field_pick(
                drop, loot, tome, found.field
            )  # remembered: identified in the field, the bad ones dropped there
        return drop
    return drop if found.sure or fielded() else None


def _new_takes(drop: Drop, mode: str, found: assess.Assessment) -> bool:
    """`_assessed_taken`'s answer by the rules alone: the field's gate, not its room (the shadow)."""
    if found.plain:
        return found.outcome == assess.Outcome.PICK
    gated = found.for_field and found.field is not None and FIELD.gate(drop)
    if mode == MOST and not (drop.source == 'shown' and oversize(drop)):
        return True
    return found.sure or gated


def _old_takes(drop: Drop, mode: str) -> bool:
    """`_taken`'s answer by the rules alone, with nothing remembered: the field's class, not its room (the shadow).
    Legacy until ASSESS_GROUND is proven."""
    based = ground_base(drop)
    if based is not None and based.pick and based.must_have and not drop.prized and _allowlisted(drop):
        drop = replace(drop, prized=True)
    if junk_base(drop, based) is not None:
        return False
    plain = plain_base(drop, based, remember=False)
    if plain is not None:
        return plain[0]
    if drop.source == 'shown' and oversize(drop):
        return based.pick if based is not None else FIELD.takes(drop) is not None
    return mode == MOST or sure(drop) or FIELD.takes(drop) is not None


# The drops the shadow compared, by game, unit, class, rolls read, level and the loop: once each
SHADOWED: set[tuple[object, ...]] = set()
SHADOWED_MOST = 4096


def _shadow(drop: Drop, mode: str, loot: Loot, found: assess.Assessment) -> None:
    """The old pickup decision beside the entry point's, one line where they differ (loot/assess.py `shadow`: "Macro:
    loot: assess: ground: magic Monarch (G6): new pick / old leave (new decides)"). Never raises into the look."""
    key = (loot.game, drop.unit_id, drop.txt, drop.rolls is not None, mode, FIELD.looping())
    if key in SHADOWED:
        return
    if len(SHADOWED) > SHADOWED_MOST:
        SHADOWED.clear()
    SHADOWED.add(key)
    try:
        new, old = _new_takes(drop, mode, found), _old_takes(drop, mode)
        title = f'{found.facts.title()} ({found.rule}, {mode})'
        word = {True: 'pick', False: 'leave'}
        assess.shadow(key, assess.Site.GROUND, title, word[new], word[old], new_decides=True)
    except Exception as error:  # never into the look
        LOG.debug('Macro: loot: assess: ground: %s not compared: %s', drop.label, error)


def next_mode(mode: str) -> str:
    """The level a KP_6 double press switches to."""
    return MODES[(MODES.index(mode) + 1) % len(MODES)]
