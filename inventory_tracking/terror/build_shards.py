"""Regenerate terror/data/shards.json: the Worldstone Shard rolls of every Hell elite.

A shard is an entry of the elite item classes (treasureclassex.txt): `Act N Worldstone Shard
Parent ...` rolls `Act N Terrorize Act Consumable` (the five shards, weighted) and `All Acts
Terrorize Consumable` (even), and their `ConditionCalc` lets the first pay outside Terror Zones
and the second inside. Negative `Picks` take the entries in order, each `Prob` times.

Which act's table an elite rolls on is not its monster's own class but the class it is
*upgraded* to: in Hell the game replaces a monster's class by the last one of the same `group`
whose `level` its monster level reaches (the classic rule; the levels are in the table). A
level-73 Catacombs champion (monster level 75) so drops from `Act 3 (H) Champ B`, whose shard
parent is Act 5's, the Northern one (user, 2026-10-07: Catacombs gave mostly Northern shards).
Runtime code (terror/shards.py) does the upgrade; this table keeps the classes and their groups.

Shard class IDs come from the item decoder's d2data copy, as the runes do (loot/build_runes.py).
Run: uv run --offline python -m inventory_tracking.terror.build_shards "<install>"
"""

import argparse
import json
import re
from pathlib import Path

from inventory_tracking.loot.build_runes import MISC
from inventory_tracking.reports import publish
from inventory_tracking.terror.build_threats import EXCEL, table
from terror_zones.game_files import GameFiles


OUTPUT = Path(__file__).parent / 'data' / 'shards.json'
TABLES = ('treasureclassex', 'monstats', 'levels', 'superuniques')
EVEN = 'All Acts Terrorize Consumable'
ACT = re.compile(r'Act (\d) Terrorize Act Consumable')
TIER = re.compile(r"stat\('heraldtier'\.accr\)\s*([<>])\s*(\d+)")
TIERS = range(1, 6)


def entries(row) -> list[tuple[str, int]]:
    return [(row[f'Item{n}'], int(row[f'Prob{n}'])) for n in range(1, 11) if row.get(f'Item{n}')]


def tier_allows(condition: str, tier: int | None) -> bool:
    """A class gated on the Herald's tier; any other condition is taken as met."""
    bounds = TIER.findall(condition or '')
    if not bounds:
        return True
    return tier is not None and all(tier > int(n) if sign == '>' else tier < int(n) for sign, n in bounds)


def shard_rolls(classes: dict[str, dict], name: str, tier: int | None = None, cache=None) -> dict[str, float]:
    """Expected rolls per kill on each shard table, for a monster dropping from class `name`."""
    cache = {} if cache is None else cache
    if name in cache:
        return cache[name]
    row = classes.get(name)
    found: dict[str, float] = {}
    if row is None or not tier_allows(row.get('ConditionCalc', ''), tier):
        return found
    if name == EVEN or ACT.fullmatch(name):
        return {name: 1.0}
    picks = int(row['Picks'] or 1)
    if picks > 0:
        total = int(row.get('NoDrop') or 0) + sum(prob for _, prob in entries(row))
        weights = [(item, picks * prob / total) for item, prob in entries(row)]
    else:
        left, weights = -picks, []
        for item, prob in entries(row):
            weights.append((item, min(prob, left)))
            left -= min(prob, left)
    for item, weight in weights:
        for leaf, rolls in shard_rolls(classes, item, tier, cache).items():
            found[leaf] = found.get(leaf, 0) + weight * rolls
    cache[name] = found
    return found


def build(tables: dict[str, list[dict[str, str]]], misc: dict, source: str) -> dict:
    classes = {row['Treasure Class']: row for row in tables['treasureclassex'] if row.get('Treasure Class')}
    monsters = {row['Id']: row for row in tables['monstats'] if row.get('TreasureClassChamp(H)')}
    supers = [row for row in tables['superuniques'] if row.get('hcIdx') and row.get('Class') in monsters]
    own = {row[column] for row in monsters.values() for column in ('TreasureClassChamp(H)', 'TreasureClassUnique(H)')}
    own |= {row['TC(H)'] for row in supers}
    lowest: dict[str, int] = {}  # group -> the level of its first class a Hell monster has
    for name in own & set(classes):
        group, level = classes[name]['group'], int(classes[name]['level'] or 0)
        if group:
            lowest[group] = min(level, lowest.get(group, level))
    groups: dict[str, list[str]] = {group: [] for group in lowest}
    for name, row in classes.items():  # file order: the upgrade walks down the group
        if row['group'] in lowest and int(row['level'] or 0) >= lowest[row['group']]:
            groups[row['group']].append(name)
    cache: dict[str, dict[str, float]] = {}
    kept = {}
    for name in sorted((own & set(classes)) | {name for names in groups.values() for name in names}):
        rolls = shard_rolls(classes, name, cache=cache)
        acts = [int(match[1]) for leaf in rolls if (match := ACT.fullmatch(leaf))]
        row = classes[name]
        kept[name] = [int(row['group'] or 0), int(row['level'] or 0), rolls.get(EVEN, 0), acts[0] if acts else 0]
    codes = [code for code, _ in entries(classes[EVEN])]
    mixes = {}
    for name, row in classes.items():
        if match := ACT.fullmatch(name):
            weights = dict(entries(row))
            mixes[match[1]] = [weights[code] for code in codes]
    heralds = {row['TreasureClassHerald(H)'] for row in monsters.values()} & set(classes)
    return {
        'source': source,
        'items': {str(misc[code]['classid']): [code, misc[code]['name']] for code in codes},
        'mixes': mixes,
        'classes': kept,
        'groups': {group: names for group, names in sorted(groups.items())},
        'monsters': {
            row['*hcIdx']: [
                row['TreasureClassChamp(H)'],
                row['TreasureClassUnique(H)'],
                int(row['Level(H)']) if row.get('boss') == '1' else 0,
            ]
            for row in monsters.values()
        },
        'supers': {row['hcIdx']: [row['TC(H)'], int(monsters[row['Class']]['*hcIdx'])] for row in supers},
        'heralds': {
            str(tier): max(shard_rolls(classes, name, tier).get(EVEN, 0) for name in sorted(heralds)) for tier in TIERS
        },
        'levels': {
            row['Id']: [int(row['Act']) + 1, int(row['MonLvlEx(H)']), row['LevelName']]
            for row in tables['levels']
            if row.get('Id') and row.get('MonLvlEx(H)')
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('install', type=Path, help='game folder (holds D2R.exe and data/)')
    args = parser.parse_args(argv)
    game = GameFiles(args.install)
    tables = {name: table(game.read(EXCEL.format(name)).decode('latin-1')) for name in TABLES}
    source = 'D2R install data/global/excel treasureclassex, monstats, levels, superuniques (2026-10-07)'
    publish(OUTPUT, build(tables, json.loads(MISC.read_text()), source))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
