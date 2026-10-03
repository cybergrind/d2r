"""Portable named-item identities and conservative numeric roll definitions.

Definitions describe possible rolls, never observed item values. Complex encoded
properties and conditional set bonuses are intentionally not scalar roll ranges.
All inputs are local; runtime consumers use a generated snapshot.
"""

import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from pricing.knowledge.base_resistances import resistance_options
from pricing.knowledge.charged_skills import charged_skills
from pricing.knowledge.localization import merge_game_strings
from pricing.knowledge.named_effects import fixed_elemental_effects, fixed_poison_effect
from pricing.knowledge.named_triggers import fixed_triggers
from pricing.knowledge.native_socket_counts import native_socket_range
from pricing.knowledge.per_level_effects import fixed_per_level_effects, variable_per_level_effects
from pricing.knowledge.property_groups import SOURCE as GROUP_SOURCE, compile_groups
from pricing.knowledge.rune_effects import socket_compound_effects
from pricing.knowledge.set_properties import has_partial_enhanced_defense, standalone_set_record


SOURCE_DATE = '2026-09-23'
# Host capture 20260923T183159Z-9b396115/request-2 + Authority tooltip.
HOST_VERIFIED_RUNEWORD_IDS = {'Authority': 20509}


def scalar_ranges(record, properties, stat_ids, *, runeword=False, skill_ids=None, affix_flat_damage=False):
    ranges = []
    for i in range(1, 13):
        code = record.get(f'T1Code{i}' if runeword else f'prop{i}')
        low = record.get(f'T1Min{i}' if runeword else f'min{i}')
        high = record.get(f'T1Max{i}' if runeword else f'max{i}')
        param = record.get(f'T1Param{i}' if runeword else f'par{i}')
        if not code or type(low) is not int or type(high) is not int or low > high:
            continue
        spec = properties.get(code, {})
        if spec.get('func1') == 21 and spec.get('stat1') == 'item_addclassskills':
            layer = spec.get('val1')
            if type(layer) is int and 0 <= layer < 8 and stat_ids.get('item_addclassskills') == 83:
                ranges.append(
                    {'stat_id': 83, 'layer': layer, 'min': low, 'max': high, 'property': code, 'better': 'higher'}
                )
            continue
        if code == 'fireskill' and spec.get('func1') == 21:
            if (
                spec.get('stat1') == 'item_elemskill'
                and spec.get('val1') == 1
                and stat_ids.get('item_elemskill') == 126
            ):
                ranges.append(
                    {'stat_id': 126, 'layer': 1, 'min': low, 'max': high, 'property': code, 'better': 'higher'}
                )
            continue
        if code == 'howl':
            low, high = low * 100 // 128, high * 100 // 128
        if code == 'skilltab' and spec.get('func1') == 10 and type(param) is int and 0 <= param < 24:
            layer = (param // 3) * 8 + param % 3
            ranges.append(
                {'stat_id': 188, 'layer': layer, 'min': low, 'max': high, 'property': code, 'better': 'higher'}
            )
            continue
        if code in ('aura', 'oskill', 'skill') and spec.get('func1') == 22:
            layer = (skill_ids or {}).get(param) if isinstance(param, str) else param
            sid = stat_ids.get(spec.get('stat1'))
            if sid is not None and type(layer) is int and layer in (skill_ids or {}).values():
                ranges.append(
                    {'stat_id': sid, 'layer': layer, 'min': low, 'max': high, 'property': code, 'better': 'higher'}
                )
            continue
        if param not in (None, '', 0):
            continue
        if affix_flat_damage and (code, spec.get('func1')) == ('dmg-min', 5):
            ids = [21, 23, 159]
        elif affix_flat_damage and (code, spec.get('func1')) == ('dmg-max', 6):
            ids = [22, 24, 160]
        elif code == 'dmg%' and spec.get('func1') == 7:
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
    result = {key(row): row for row in ranges if counts[key(row)] == 1}
    if runeword:
        # Recipe resistance properties add. Only fixed contributions may be
        # collapsed: variable res-all must retain its shared-roll constraint.
        for stat, code in ((39, 'res-fire'), (41, 'res-ltng'), (43, 'res-cold'), (45, 'res-pois')):
            parts = [row for row in ranges if key(row) == str(stat)]
            if len(parts) > 1 and all(
                row['property'] in (code, 'res-all') and row['min'] == row['max'] for row in parts
            ):
                total = sum(row['min'] for row in parts)
                result[str(stat)] = {**parts[0], 'min': total, 'max': total, 'property': code}
    return result


def socket_bonus_ranges(runes, gems, properties, stat_ids):
    """Compile supported scalar rune effects by destination equipment family."""
    result = {}
    for family, prefix in [('weapon', 'weapon'), ('shield', 'shield'), ('armor', 'helm'), ('helm', 'helm')]:
        totals = {}
        if any(code not in gems for code in runes):
            result[family] = totals
            continue
        for code in runes:
            gem = gems[code]
            record = {}
            for i in range(1, 4):
                for target, suffix in [('prop', 'Code'), ('min', 'Min'), ('max', 'Max'), ('par', 'Param')]:
                    record[f'{target}{i}'] = gem.get(f'{prefix}Mod{i}{suffix}')
            for key, spec in scalar_ranges(record, properties, stat_ids).items():
                if key in totals:
                    totals[key]['min'] += spec['min']
                    totals[key]['max'] += spec['max']
                else:
                    totals[key] = dict(spec)
        result[family] = totals
    return result


def range_family(definition):
    # Local properties.json: cast1/cast2/cast3 all use func8/item_fastercastrate.
    if definition.get('stat_id') == 105 and definition['property'] in ('cast1', 'cast2', 'cast3'):
        return 'faster_cast_rate'
    return definition['property']


def add_charm_quality_ranges(rows, *, rare=False):
    """Rank against current spawnable tiers, separately from the item's own tier."""
    from pricing.knowledge.assessment.mechanics.affix_pool import can_generate

    pools = {}
    tiers = {}
    for entry in rows:
        if not entry.get('affix_table'):
            continue
        for base in entry['base_codes']:
            if not can_generate(entry, base, 'rare' if rare else 'magic'):
                continue
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
    property_groups = read(GROUP_SOURCE)
    stats = read('third-parties/d2data/json/itemstatcost.json')
    stat_ids = {key: row['*ID'] for key, row in stats.items()}
    skill_ids = {
        r['skill']: r['*Id']
        for r in read('third-parties/d2data/json/skills.json').values()
        if 'skill' in r and '*Id' in r
    }
    # Planner strings omit recent item identities; the pinned English game
    # table supplies their display names while retaining established translations.
    strings = merge_game_strings(
        read('third-parties/d2data/json/allstrings-eng.json'),
        read('pricing/raw/mr/planners/game-strings.json'),
    )
    bases = {}
    for category in ('weapons', 'armor', 'misc'):
        bases.update(read(raw + category + '.json'))
    types = read(raw + 'itemtypes.json')
    automagic = read('third-parties/d2data/json/automagic.json')

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

    def compile_named(record, quality, code_key, source_path, set_definitions=None):
        effects = standalone_set_record(record) if quality == 'set' else record
        code = record.get(code_key)
        base_defense = bases.get(code, {})
        plain_defense = type(base_defense.get('minac')) is int and not any(
            str(effects.get(f'prop{i}', '')).startswith('ac') for i in range(1, 13)
        )
        fixed_base_defense = quality == 'set' and has_partial_enhanced_defense(record)
        return {
            'base_defense_range': (
                {
                    'min': base_defense['maxac'] + 1 if fixed_base_defense else base_defense['minac'],
                    'max': base_defense['maxac'] + 1 if fixed_base_defense else base_defense['maxac'],
                    'source': {'path': raw + 'armor.json', 'source_date': SOURCE_DATE},
                }
                if plain_defense
                else None
            ),
            'kind': 'item_definition',
            'name': strings.get(record['index'], record['index']),
            'rarity': quality,
            'table_id': record['*ID'],
            'set_definition': (sets if set_definitions is None else set_definitions).get(record.get('set')),
            'game_definition': dict(record),
            'base_definition': dict(bases.get(code, {})),
            'native_socket_range': native_socket_range(effects, bases.get(code, {}), types),
            'base_code': code,
            'base_codes': [code] if code in bases else [],
            'base_name': bases.get(code, {}).get('name'),
            'set_name': strings.get(record.get('set'), record.get('set')),
            'roll_ranges': scalar_ranges(effects, properties, stat_ids, skill_ids=skill_ids),
            'property_groups': compile_groups(
                effects,
                property_groups,
                lambda row: scalar_ranges(row, properties, stat_ids, skill_ids=skill_ids),
                inputs[GROUP_SOURCE],
            ),
            'fixed_elemental_effects': fixed_elemental_effects(effects, properties),
            'fixed_poison_effect': fixed_poison_effect(effects, properties),
            'fixed_triggers': fixed_triggers(effects, properties, stat_ids, skill_ids),
            'fixed_per_level_effects': fixed_per_level_effects(effects, properties, stats),
            'variable_per_level_effects': variable_per_level_effects(effects, properties, stats),
            'enhanced_damage_expected': any(effects.get(f'prop{i}') == 'dmg%' for i in range(1, 13)),
            'source': {'path': source_path, 'source_date': SOURCE_DATE},
        }

    ordinary_path = 'third-parties/d2data/json/base/uniqueitems.json'
    from pricing.knowledge.non_ladder_named import ITEMS, NAMES, UNIQUE_IDS, ordinary_angelic, ordinary_unique_records

    ordinary_set_items, ordinary_sets, set_mode_review = ordinary_angelic(root, read, inputs)
    ordinary_unique_items, unique_mode_review = ordinary_unique_records(root, read, inputs)
    for quality, filename, code_key in (('set', 'setitems', 'item'), ('unique', 'uniqueitems', 'code')):
        source_path = raw + filename + '.json'
        records = read(source_path)
        ordinary = None
        for key, record in records.items():
            row = compile_named(record, quality, code_key, source_path)
            if quality == 'set' and record['index'] in NAMES:
                original = ordinary_set_items.get(key)
                if original is None or any(original.get(k) != record.get(k) for k in ('*ID', 'index', 'item', 'set')):
                    raise ValueError(f'Conflicting ordinary Angelic definition: {key}')
                ladder = row
                row = compile_named(original, quality, code_key, ITEMS, ordinary_sets)
                row['ladder_definition'] = ladder
                row['mode_review'] = set_mode_review
            if quality == 'unique' and record.get('firstLadderSeason') == record.get('lastLadderSeason') == 15:
                # A season overlay can reuse the ordinary table ID. Preserve the
                # old definition inside the indexed identity, with its own source.
                if ordinary is None:
                    ordinary = read(ordinary_path)
                original = ordinary.get(key)
                if original is None or any(original.get(k) != record.get(k) for k in ('*ID', 'index', 'code')):
                    raise ValueError(f'Conflicting ordinary seasonal definition: {key}')
                if original != record:
                    ordinary_row = compile_named(original, quality, code_key, ordinary_path)
                    if record['*ID'] in UNIQUE_IDS:
                        if original != ordinary_unique_items[key]:
                            raise ValueError('Ordinary unique source disagreement')
                        ordinary_row['ladder_definition'] = row
                        ordinary_row['mode_review'] = unique_mode_review
                        row = ordinary_row
                    else:
                        row['ordinary_definition'] = ordinary_row
            rows.append(row)
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
    gems = read('third-parties/d2data/json/gems.json')
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
                'fixed_triggers': fixed_triggers(record, properties, stat_ids, skill_ids, runeword=True),
                'charged_skills': charged_skills(record, properties, skill_ids),
                'fixed_per_level_effects': fixed_per_level_effects(record, properties, stats, runeword=True),
                'variable_per_level_effects': variable_per_level_effects(record, properties, stats, runeword=True),
                'fixed_elemental_effects': fixed_elemental_effects(record, properties, runeword=True),
                'base_resistance_options': {code: resistance_options(bases[code], automagic) for code in codes},
                'base_stat_ranges': {
                    code: {
                        '20': {
                            'stat_id': 20,
                            'min': bases[code]['block'],
                            'max': bases[code]['block'],
                            'property': 'base_block',
                        }
                    }
                    for code in codes
                    if matches(bases[code].get('type'), {'shld'}) and type(bases[code].get('block')) is int
                },
                'socket_compound_effects': socket_compound_effects(
                    [record[f'Rune{i}'] for i in range(1, 7) if record.get(f'Rune{i}')], gems, properties
                ),
                'socket_bonus_ranges': socket_bonus_ranges(
                    [record[f'Rune{i}'] for i in range(1, 7) if record.get(f'Rune{i}')], gems, properties, stat_ids
                ),
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
    # ItemMode.cpp:6288-6290 supplies the base's auto-prefix group;
    # ItemsMagic.cpp:327 also requires that group to match the automagic row.
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
                if matches(b.get('type'), allowed)
                and not matches(b.get('type'), excluded)
                and (
                    table != 'auto'
                    or (
                        type(record.get('group')) is int
                        and record['group'] > 0
                        and b.get('auto prefix') == record['group']
                    )
                )
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
                    'roll_ranges': scalar_ranges(
                        normalized, properties, stat_ids, skill_ids=skill_ids, affix_flat_damage=True
                    ),
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
        patterns = {}
        for index, record in quality_records.items():
            if not record.get(gate):
                continue
            patterns[str(index)] = dict(record)
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
                'patterns': patterns,
                'rarity': 'superior',
                'category': category,
                'table_id': None,
                'roll_ranges': {k: {**v, 'tiers': [{'min': v['min'], 'max': v['max']}]} for k, v in bounds.items()},
                'source': {'path': quality_path, 'source_date': SOURCE_DATE},
            }
        )
    pools = compact_affix_pools(rows)
    from pricing.knowledge.crafting_bases import crafting_bases, nonethereal_crafting_recipes
    from pricing.knowledge.crafting_cold import crafting_affix_only_cold
    from pricing.knowledge.crafting_poison import crafting_affix_only_poison
    from pricing.knowledge.crafting_triggers import crafting_triggers

    cube_recipes = read('third-parties/d2data/json/cubemain.json')
    craft_bases = crafting_bases(cube_recipes, bases)
    return {
        'schema_version': 1,
        'source_date': SOURCE_DATE,
        'inputs': inputs,
        'rows': rows,
        'crafting_bases': craft_bases,
        'crafting_affix_only_cold': crafting_affix_only_cold(cube_recipes, bases, properties, matches),
        'crafting_affix_only_poison': crafting_affix_only_poison(cube_recipes, bases, properties, matches),
        'crafting_nonethereal': nonethereal_crafting_recipes(cube_recipes),
        'crafting_triggers': crafting_triggers(cube_recipes, bases, properties, stat_ids, skill_ids, matches),
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
    payload = json.dumps(build_definitions(args.root), indent=2) + '\n'
    with tempfile.NamedTemporaryFile(mode='w', dir=output.parent, prefix=output.name + '.', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
