"""Portable named-item identities and conservative numeric roll definitions.

Definitions describe possible rolls, never observed item values. Complex encoded
properties and conditional set bonuses are intentionally not scalar roll ranges.
All inputs are local; runtime consumers use a generated snapshot.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


SOURCE_DATE = '2026-09-23'
# Host capture 20260923T183159Z-9b396115/request-2 + Authority tooltip.
HOST_VERIFIED_RUNEWORD_IDS = {'Authority': 20509}


def scalar_ranges(record, properties, stat_ids, *, runeword=False, skill_ids=None):
    ranges = []
    for i in range(1, 13):
        code = record.get(f'T1Code{i}' if runeword else f'prop{i}')
        low = record.get(f'T1Min{i}' if runeword else f'min{i}')
        high = record.get(f'T1Max{i}' if runeword else f'max{i}')
        param = record.get(f'T1Param{i}' if runeword else f'par{i}')
        if not code or type(low) is not int or type(high) is not int or low > high:
            continue
        spec = properties.get(code, {})
        if code == 'howl':
            low, high = low * 100 // 128, high * 100 // 128
        if code == 'skilltab' and spec.get('func1') == 10 and type(param) is int and 0 <= param < 24:
            layer = (param // 3) * 8 + param % 3
            ranges.append(
                {'stat_id': 188, 'layer': layer, 'min': low, 'max': high, 'property': code, 'better': 'higher'}
            )
            continue
        if code in ('aura', 'oskill') and spec.get('func1') == 22:
            layer = (skill_ids or {}).get(param) if isinstance(param, str) else param
            sid = stat_ids.get(spec.get('stat1'))
            if sid is not None and type(layer) is int and layer in (skill_ids or {}).values():
                ranges.append(
                    {'stat_id': sid, 'layer': layer, 'min': low, 'max': high, 'property': code, 'better': 'higher'}
                )
            continue
        if param not in (None, '', 0):
            continue
        if code == 'dmg%' and spec.get('func1') == 7:
            ids = [17, 18]
        elif spec.get('func1') in (1, 2, 8, 14):
            ids = []
            for n in range(1, 8):
                name = spec.get(f'stat{n}')
                if name and spec.get(f'func{n}') in (1, 2, 3, 8, 14) and name in stat_ids:
                    ids.append(stat_ids[name])
        else:
            continue
        ranges.extend(
            {
                'stat_id': sid,
                'min': low,
                'max': high,
                'property': code,
                'better': 'lower' if code == 'ease' else 'higher',
            }
            for sid in ids
        )

    def key(row):
        return f'{row["stat_id"]}:{row["layer"]}' if 'layer' in row else str(row['stat_id'])

    counts = Counter(key(row) for row in ranges)
    return {key(row): row for row in ranges if counts[key(row)] == 1}


def range_family(definition):
    # Local properties.json: cast1/cast2/cast3 all use func8/item_fastercastrate.
    if definition.get('stat_id') == 105 and definition['property'] in ('cast1', 'cast2', 'cast3'):
        return 'faster_cast_rate'
    return definition['property']


def add_charm_quality_ranges(rows, *, rare=False):
    """Rank against current spawnable tiers, separately from the item's own tier."""
    pools = {}
    tiers = {}
    for entry in rows:
        if not entry.get('affix_table') or not entry.get('spawnable') or (rare and not entry.get('rare')):
            continue
        for base in entry['base_codes']:
            for stat, definition in entry['roll_ranges'].items():
                key = (base, entry['affix_table'], stat, range_family(definition))
                tiers.setdefault(key, set()).add((definition['min'], definition['max']))
                pool = pools.setdefault(key, {'min': definition['min'], 'max': definition['max']})
                pool['min'] = min(pool['min'], definition['min'])
                pool['max'] = max(pool['max'], definition['max'])
    for entry in rows:
        if not entry.get('affix_table'):
            continue
        entry['rare_roll_tiers' if rare else 'roll_tiers'] = {
            base: {
                stat: [
                    {'min': low, 'max': high}
                    for low, high in sorted(
                        tiers[key], key=lambda pair: (pair[1], pair[0]), reverse=definition.get('better') != 'lower'
                    )
                ]
                for stat, definition in entry['roll_ranges'].items()
                if (key := (base, entry['affix_table'], stat, range_family(definition))) in tiers
            }
            for base in entry['base_codes']
        }
        entry['rare_quality_ranges' if rare else 'quality_ranges'] = {
            base: {
                stat: dict(pools[key])
                for stat, definition in entry['roll_ranges'].items()
                if (key := (base, entry['affix_table'], stat, range_family(definition))) in pools
            }
            for base in entry['base_codes']
        }


def compact_affix_pools(rows):
    """Share identical tier ladders across affixes and compatible bases."""
    pools = {}
    keys = {}
    for entry in rows:
        if not entry.get('affix_table'):
            continue
        for prefix in ('', 'rare_'):
            tiers = entry.pop(prefix + 'roll_tiers')
            ranges = entry.pop(prefix + 'quality_ranges')
            references = {}
            for base, stats in tiers.items():
                references[base] = {}
                for stat, ladder in stats.items():
                    value = {'tiers': ladder, 'range': ranges[base][stat]}
                    key = json.dumps(value, sort_keys=True)
                    if key not in keys:
                        pool_id = str(len(keys))
                        keys[key] = pool_id
                        pools[pool_id] = value
                    references[base][stat] = keys[key]
            entry[prefix + 'range_pools'] = references
    return pools


def build_definitions(root):
    root = Path(root)
    inputs = {}

    def read(path):
        data = (root / path).read_bytes()
        inputs[path] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    raw = 'pricing/raw/d2data/'
    properties = read('third-parties/d2data/json/properties.json')
    stats = read('third-parties/d2data/json/itemstatcost.json')
    stat_ids = {key: row['*ID'] for key, row in stats.items()}
    skill_ids = {
        r['skill']: r['*Id']
        for r in read('third-parties/d2data/json/skills.json').values()
        if 'skill' in r and '*Id' in r
    }
    strings = {
        r[0]: r[1] for r in read('pricing/raw/mr/planners/game-strings.json') if isinstance(r, list) and len(r) == 2
    }
    bases = {}
    for category in ('weapons', 'armor', 'misc'):
        bases.update(read(raw + category + '.json'))
    types = read(raw + 'itemtypes.json')

    def matches(code, allowed, seen=None):
        seen = set() if seen is None else seen
        if code in allowed:
            return True
        if not code or code in seen:
            return False
        seen.add(code)
        return any(matches(types.get(code, {}).get(key), allowed, seen) for key in ('Equiv1', 'Equiv2'))

    sets = read('third-parties/d2data/json/sets.json')
    rows: list[dict[str, Any]] = []
    for quality, filename, code_key in (('set', 'setitems', 'item'), ('unique', 'uniqueitems', 'code')):
        for record in read(raw + filename + '.json').values():
            code = record.get(code_key)
            base_defense = bases.get(code, {})
            plain_defense = type(base_defense.get('minac')) is int and not any(
                str(record.get(f'prop{i}', '')).startswith('ac') for i in range(1, 13)
            )
            rows.append(
                {
                    'base_defense_range': (
                        {
                            'min': base_defense['minac'],
                            'max': base_defense['maxac'],
                            'source': {'path': raw + 'armor.json', 'source_date': SOURCE_DATE},
                        }
                        if plain_defense
                        else None
                    ),
                    'kind': 'item_definition',
                    'name': strings.get(record['index'], record['index']),
                    'rarity': quality,
                    'table_id': record['*ID'],
                    'set_definition': sets.get(record.get('set')),
                    'game_definition': dict(record),
                    'base_definition': dict(bases.get(code, {})),
                    'base_code': code,
                    'base_codes': [code] if code in bases else [],
                    'base_name': bases.get(code, {}).get('name'),
                    'set_name': strings.get(record.get('set'), record.get('set')),
                    'roll_ranges': scalar_ranges(record, properties, stat_ids, skill_ids=skill_ids),
                    'enhanced_damage_expected': any(record.get(f'prop{i}') == 'dmg%' for i in range(1, 13)),
                    'source': {'path': raw + filename + '.json', 'source_date': SOURCE_DATE},
                }
            )
    # The client stores a runeword string ID in the first prefix slot. Use the
    # checked-in reader's explicit mapping, not guessed table row arithmetic.
    mapping_path = 'third-parties/d2go/pkg/data/item/runeword.go'
    text = (root / mapping_path).read_text()
    inputs[mapping_path] = hashlib.sha256((root / mapping_path).read_bytes()).hexdigest()
    names = dict(re.findall(r'(Runeword\w+)\s+RunewordName\s*=\s*"([^"]+)"', text))
    ids = {
        names[symbol]: int(value) for value, symbol in re.findall(r'(\d+):\s*(Runeword\w+)', text) if symbol in names
    }
    for name, table_id in HOST_VERIFIED_RUNEWORD_IDS.items():
        if name in ids and ids[name] != table_id:
            raise ValueError(f'Conflicting runeword ID for {name}')
        ids[name] = table_id
    for name, record in read(raw + 'runes.json').items():
        if record.get('complete') != 1:
            continue
        allowed = {record[f'itype{i}'] for i in range(1, 7) if record.get(f'itype{i}')}
        excluded = {record[f'etype{i}'] for i in range(1, 4) if record.get(f'etype{i}')}
        codes = [
            code
            for code, b in bases.items()
            if matches(b.get('type'), allowed) and not matches(b.get('type'), excluded)
        ]
        rows.append(
            {
                'kind': 'item_definition',
                'name': name,
                'rarity': 'runeword',
                'table_id': ids.get(name),
                'base_codes': codes,
                'runes': [record[f'Rune{i}'] for i in range(1, 7) if record.get(f'Rune{i}')],
                'roll_ranges': scalar_ranges(record, properties, stat_ids, runeword=True, skill_ids=skill_ids),
                'enhanced_damage_expected': any(record.get(f'T1Code{i}') == 'dmg%' for i in range(1, 8)),
                'source': {'path': raw + 'runes.json', 'source_date': SOURCE_DATE},
            }
        )
    # The engine concatenates suffix then prefix records and uses 1-based IDs
    # (D2MOO ItemsTbls.cpp). JSON keys retain expansion-marker gaps; enumerate
    # actual records, not key numbers. RotW has more suffixes than old d2go.
    suffixes = read('third-parties/d2data/json/magicsuffix.json')
    prefixes = read('third-parties/d2data/json/magicprefix.json')
    automagic = read('third-parties/d2data/json/automagic.json')
    for table, records, offset in (
        ('suffix', suffixes, 0),
        ('prefix', prefixes, len(suffixes)),
        ('auto', automagic, len(suffixes) + len(prefixes)),
    ):
        for ordinal, key in enumerate(sorted(records, key=int), 1):
            record = records[key]
            allowed = {record[f'itype{i}'] for i in range(1, 8) if record.get(f'itype{i}')}
            excluded = {record[f'etype{i}'] for i in range(1, 6) if record.get(f'etype{i}')}
            codes = [
                code
                for code, b in bases.items()
                if matches(b.get('type'), allowed) and not matches(b.get('type'), excluded)
            ]
            if not codes or not record.get('Name'):
                continue
            normalized = {}
            for i in range(1, 4):
                for target, source in (('prop', 'code'), ('min', 'min'), ('max', 'max'), ('par', 'param')):
                    normalized[f'{target}{i}'] = record.get(f'mod{i}{source}')
            rows.append(
                {
                    'kind': 'item_definition',
                    'name': record['Name'],
                    'rarity': 'magic',
                    'game_definition': dict(record),
                    'affix_table': table,
                    'spawnable': record.get('spawnable') == 1,
                    'rare': record.get('rare') == 1,
                    'table_id': offset + ordinal,
                    'base_codes': codes,
                    'roll_ranges': scalar_ranges(normalized, properties, stat_ids, skill_ids=skill_ids),
                    'source': {
                        'path': (
                            'third-parties/d2data/json/automagic.json'
                            if table == 'auto'
                            else f'third-parties/d2data/json/magic{table}.json'
                        ),
                        'source_date': SOURCE_DATE,
                        'record_key': key,
                    },
                }
            )
    add_charm_quality_ranges(rows)
    add_charm_quality_ranges(rows, rare=True)
    rare_suffixes = read('third-parties/d2data/json/raresuffix.json')
    rare_prefixes = read('third-parties/d2data/json/rareprefix.json')
    rare_names = {}
    for table, records, offset in (('prefix', rare_prefixes, len(rare_suffixes)), ('suffix', rare_suffixes, 0)):
        rare_names[table] = {}
        for ordinal, key in enumerate(sorted(records, key=int), 1):
            record = records[key]
            allowed = {record[f'itype{i}'] for i in range(1, 8) if record.get(f'itype{i}')}
            excluded = {record[f'etype{i}'] for i in range(1, 6) if record.get(f'etype{i}')}
            rare_names[table][str(offset + ordinal)] = {
                'name': record['name'].title(),
                'base_codes': [
                    code
                    for code, base in bases.items()
                    if matches(base.get('type'), allowed) and not matches(base.get('type'), excluded)
                ],
            }
    quality_path = 'third-parties/d2data/json/qualityitems.json'
    quality_records = read(quality_path)
    for category, gate in (('weapons', 'weapon'), ('armor', 'armor')):
        bounds = {}
        for record in quality_records.values():
            if not record.get(gate):
                continue
            normalized = {
                f'{target}{i}': record.get(f'mod{i}{suffix}')
                for i in (1, 2)
                for target, suffix in (('prop', 'code'), ('min', 'min'), ('max', 'max'), ('par', 'param'))
            }
            for stat, definition in scalar_ranges(normalized, properties, stat_ids).items():
                if stat in bounds and bounds[stat] != definition:
                    raise ValueError('Conflicting superior ranges')
                bounds[stat] = definition
        rows.append(
            {
                'kind': 'quality_definition',
                'name': f'Superior {category}',
                'rarity': 'superior',
                'category': category,
                'table_id': None,
                'roll_ranges': {k: {**v, 'tiers': [{'min': v['min'], 'max': v['max']}]} for k, v in bounds.items()},
                'source': {'path': quality_path, 'source_date': SOURCE_DATE},
            }
        )
    pools = compact_affix_pools(rows)
    return {
        'schema_version': 1,
        'source_date': SOURCE_DATE,
        'inputs': inputs,
        'rows': rows,
        'staffmods': {
            'classes_by_type': {code: r['StaffMods'] for code, r in types.items() if r.get('StaffMods')},
            'range': {'min': 1, 'max': 3},
            'inferior_range': {'min': 1, 'max': 1},
            'source': {
                'path': 'third-parties/D2MOO/source/D2Game/src/ITEMS/Items.cpp',
                'symbol': 'sub_6FC52650',
                'source_date': SOURCE_DATE,
            },
        },
        'affix_pools': pools,
        'rare_names': rare_names,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, default=Path('pricing/data/appraisal-definitions.json'))
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.write_text(json.dumps(build_definitions(args.root), indent=2) + '\n')


if __name__ == '__main__':
    main()
