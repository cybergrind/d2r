"""Drops the pickup step takes because the loot filter shows them (user, 2026-10-11).

The filter (lootfilter/warlock_lean_v2.json, the one profile; loot/build_filter.py rebuilds its unique and set
rules) decides "worth a look"; its Show rules are read here so what the game labels is what is picked up, and the
two cannot drift. A rule matches as the game does (the lootfilter skill): rarity AND (category OR item code);
`filterEtherealSocketed` adds gray items. Accessories are left out: they are groups of loot/materials.py.

Smaller items are preferred (user, 2026-10-11): below set quality only bases of at most `max_cells` cells are
taken. Gems follow the game's own copy of the profile (`game_filter`; user, 2026-10-12: "I want to get some
chipped gems and enabled it myself").
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from inventory_tracking.common import LOG
from inventory_tracking.config import SHOW_ITEMS
from inventory_tracking.items.identity import ETHEREAL_FLAG, IDENTIFIED_FLAG, SOCKETED_FLAG
from inventory_tracking.items.metadata import metadata


FILTER = Path(__file__).resolve().parents[2] / 'lootfilter' / 'warlock_lean_v2.json'
# The player, 2026-10-22 ~08:31: "why we're trying to pickup gothic staff that are hidden by our loot filter?" The game
# shows what its own copy of the profile says (`game_filter`, rewritten at each import), and that copy had 19 rules, the
# repo file 23: the four Show rules of 2026-10-20 ~18:45 (SHOW Staff Mod Staves Gray among them) were never imported.
# The pickup read the repo file, took a Superior Gothic Staff for shown, and its clicks found no label to take
# (rca/2026-10-22/hidden-staff-findings.md). True: the gear rules come from the game's copy too, as the gems' do
# (`profile`); the repo file when there is none or it cannot be read. False: the repo file, as before
GAME_COPY = True
UNREADABLE: set[Path] = set()  # the profiles whose game copy was said unreadable, once each
SIZES = Path(__file__).parent / 'data' / 'sizes.json'
# The filter's rarity names -> ItemData quality, and the word a row label starts with.
RARITIES = {'lowQuality': 1, 'normal': 2, 'hiQuality': 3, 'magic': 4, 'set': 5, 'rare': 6, 'unique': 7}
WORDS = {1: 'Low Quality', 2: '', 3: 'Superior', 4: 'Magic', 5: 'Set', 6: 'Rare', 7: 'Unique'}
GRAY_QUALITIES = frozenset((1, 2, 3))
NAMED_QUALITIES = frozenset((5, 7))  # taken at any size
# The filter's equipment categories -> the decoder's base types (the lootfilter skill's category codes).
CATEGORIES = {
    'glove': ('glov',),
    'boots': ('boot',),
    'belts': ('belt',),
    'circl': ('circ',),
    'warlo': ('grim',),
    'barbh': ('phlm',),
    'necro': ('head',),
    'druid': ('pelt',),
    'sorce': ('orb',),
    'palad': ('ashd',),
    'assas': ('h2h', 'h2h2'),
    'amazo': ('abow', 'aspe', 'ajav'),
}
ACCESSORIES = 'acce'
GEMS = 'gems'  # the filter's item category of every gem and skull
# The decoder's base types of the gems: sapphire, emerald, ruby, amethyst, diamond, topaz, skull.
GEM_TYPES = frozenset(('gems', 'geme', 'gemr', 'gema', 'gemd', 'gemt', 'gemz'))
EQUIPMENT = frozenset(('armor', 'weapons'))  # the decoder's base categories a Show rule has to list


@dataclass(frozen=True)
class ShownRule:
    """One Show rule of the filter, by item class."""

    qualities: frozenset[int]
    gray: bool  # also an ethereal or socketed low, normal or superior item
    classes: frozenset[int]


@cache
def filter_rules(path: Path = FILTER, stamp: int = 0) -> tuple[ShownRule, ...]:
    """The filter's enabled Show rules for equipment, without the accessories. `stamp`: only a cache key (`profile`'s
    file time), so a profile the game rewrote is read again."""
    bases = metadata()['bases']
    by_code = {base['code']: int(class_id) for class_id, base in bases.items()}
    rules = []
    for rule in json.loads(path.read_text())['rules']:
        if rule['ruleType'] != 'show' or not rule['enabled'] or not rule.get('equipmentRarity'):
            continue
        types = {kind for name in rule.get('equipmentCategory', []) if name != ACCESSORIES for kind in CATEGORIES[name]}
        classes = {by_code[code] for code in rule.get('equipmentItemCode', [])}
        classes |= {int(class_id) for class_id, base in bases.items() if base.get('type') in types}
        if classes:
            qualities = frozenset(RARITIES[name] for name in rule['equipmentRarity'])
            rules.append(ShownRule(qualities, bool(rule.get('filterEtherealSocketed')), frozenset(classes)))
    return tuple(rules)


def game_filter(path: Path = FILTER, saved_games: Path = SHOW_ITEMS.saved_games) -> Path:
    """The game's copy of the profile (`<name>.fltr` in saved games, rewritten by its filter editor), else `path`."""
    copy = saved_games / f'{json.loads(path.read_text())["name"]}.fltr'
    return copy if copy.exists() else path


def profile(path: Path = FILTER, saved_games: Path | None = None) -> tuple[Path, int]:
    """(the profile the gear rules are read from, its file time as a cache key): the game's copy (GAME_COPY) when
    `filter_rules` reads it, else `path`."""
    if GAME_COPY:
        try:
            copy = game_filter(path) if saved_games is None else game_filter(path, saved_games)
            if copy != path:
                stamp = copy.stat().st_mtime_ns
                filter_rules(copy, stamp)
                return copy, stamp
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if path not in UNREADABLE:
                UNREADABLE.add(path)
                LOG.info("Macro: the game's copy of the loot filter could not be read (%r): the repo file is read", exc)
    return path, 0


def shown_gems(path: Path) -> dict[int, str]:
    """Item class ID -> name of the gems and skulls an enabled Show rule lists (by code, or all by category)."""
    codes, every = set(), False
    for rule in json.loads(path.read_text())['rules']:
        if rule['ruleType'] == 'show' and rule['enabled']:
            codes.update(rule.get('itemCode', []))
            every = every or GEMS in rule.get('itemCategory', [])
    return {
        int(class_id): base['name']
        for class_id, base in metadata()['bases'].items()
        if base.get('type') in GEM_TYPES and (every or base['code'] in codes)
    }


@cache
def pickup_rules(max_cells: int, path: Path = FILTER, stamp: int = 0) -> tuple[ShownRule, ...]:
    """The filter's rules for the pickup step: below set quality only bases of at most `max_cells` cells."""
    sizes = {int(class_id): size[0] * size[1] for class_id, size in json.loads(SIZES.read_text())['sizes'].items()}
    rules = []
    for rule in filter_rules(path, stamp):
        if rule.qualities <= NAMED_QUALITIES:
            rules.append(rule)
            continue
        small = frozenset(class_id for class_id in rule.classes if sizes.get(class_id, 1) <= max_cells)
        if small:
            rules.append(ShownRule(rule.qualities - NAMED_QUALITIES, rule.gray, small))
    return tuple(rules)


@cache
def oversize_rules(
    max_cells: int, qualities: frozenset[int], path: Path = FILTER, stamp: int = 0
) -> tuple[ShownRule, ...]:
    """The filter's rules for the bases over `max_cells` cells that `pickup_rules` leaves out, for `qualities` alone
    (a gray item counts when `qualities` holds a white quality): the cap lifted only for what the loop judges before
    it carries it (2026-10-20, macros/pickup.py `wanted`: the field identify's magic and rare items, the ground read's
    white bases). Every such drop is still judged by macros/pickmode.py `kept`, in every pickup level."""
    sizes = {int(class_id): size[0] * size[1] for class_id, size in json.loads(SIZES.read_text())['sizes'].items()}
    rules = []
    for rule in filter_rules(path, stamp):
        if rule.qualities <= NAMED_QUALITIES:
            continue
        big = frozenset(class_id for class_id in rule.classes if sizes.get(class_id, 1) > max_cells)
        taken = (rule.qualities - NAMED_QUALITIES) & qualities
        gray = rule.gray and bool(qualities & GRAY_QUALITIES)
        if big and (taken or gray):
            rules.append(ShownRule(frozenset(taken), gray, big))
    return tuple(rules)


def hides(rules, class_id: int, quality: int) -> bool:
    """Whether the filter hides an item of this base and quality: an armor or weapon no rule shows."""
    if metadata()['bases'][str(class_id)]['category'] not in EQUIPMENT:
        return False
    return not any(class_id in rule.classes and quality in rule.qualities for rule in rules)


def shown_label(rules, class_id: int, quality: int, flags: int) -> str | None:
    """The row label of a ground item some rule shows, or None. An identified magic-or-better one was read
    and dropped by the player."""
    if quality > 3 and flags & IDENTIFIED_FLAG:
        return None
    gray = quality in GRAY_QUALITIES and bool(flags & (ETHEREAL_FLAG | SOCKETED_FLAG))
    if not any(class_id in rule.classes and (quality in rule.qualities or (rule.gray and gray)) for rule in rules):
        return None
    words = ['Ethereal' if flags & ETHEREAL_FLAG else '', 'Socketed' if flags & SOCKETED_FLAG else '']
    words += [WORDS.get(quality, ''), metadata()['bases'][str(class_id)]['name']]
    return ' '.join(word for word in words if word)
