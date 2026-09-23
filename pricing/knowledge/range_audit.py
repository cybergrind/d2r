"""Audit every local unique/set property without treating all Min/Max pairs as rolls."""

import argparse
import json
from collections import Counter
from pathlib import Path

from pricing.knowledge.definitions import build_definitions


def audit_ranges(root):
    root = Path(root)
    definitions = build_definitions(root)
    indexed = {(r['rarity'], r['table_id']): r for r in definitions['rows'] if r['rarity'] in ('set', 'unique')}
    properties = json.loads((root / 'third-parties/d2data/json/properties.json').read_text())
    items = []
    for rarity, table in (('unique', 'uniqueitems'), ('set', 'setitems')):
        records = json.loads((root / f'pricing/raw/d2data/{table}.json').read_text())
        for record in records.values():
            definition = indexed[rarity, record['*ID']]
            supported = {r['property'] for r in definition['roll_ranges'].values()}
            entries = []
            slots = [(f'prop{i}', f'min{i}', f'max{i}', f'par{i}', False) for i in range(1, 13)]
            slots += [
                (f'aprop{i}{suffix}', f'amin{i}{suffix}', f'amax{i}{suffix}', f'apar{i}{suffix}', True)
                for i in range(1, 6)
                for suffix in ('a', 'b')
            ]
            for code_key, low_key, high_key, param_key, conditional in slots:
                code = record.get(code_key)
                if not code:
                    continue
                low, high = record.get(low_key), record.get(high_key)
                function = properties.get(code, {}).get('func1')
                if conditional:
                    status = 'conditional_set_bonus_review'
                elif code in supported:
                    status = 'covered_scalar_range' if low != high else 'fixed_scalar'
                elif function == 15:
                    status = 'damage_endpoints_not_roll_bounds'
                elif function in (11, 19, 24):
                    status = 'encoded_property_review'
                elif type(low) is int and type(high) is int and low != high:
                    status = 'uncovered_variable_or_encoding'
                else:
                    status = 'fixed_or_parameterized_review'
                entries.append(
                    {
                        'slot': code_key,
                        'property': code,
                        'min': low,
                        'max': high,
                        'param': record.get(param_key),
                        'function': function,
                        'status': status,
                    }
                )
            items.append(
                {
                    'name': definition['name'],
                    'rarity': rarity,
                    'table_id': record['*ID'],
                    'base_code': definition['base_code'],
                    'base_defense_range': definition['base_defense_range'],
                    'properties': entries,
                }
            )
    counts = Counter(p['status'] for item in items for p in item['properties'])
    return {
        'source_date': definitions['source_date'],
        'inputs': definitions['inputs'],
        'complete_range_coverage': False,
        'item_count': len(items),
        'property_counts': dict(counts),
        'items': items,
    }


def render_audit(audit):
    lines = [
        '# Unique/set roll-range audit',
        '',
        f'Source date: {audit["source_date"]}. {audit["item_count"]} definitions checked.',
        '',
        'Coverage is incomplete. This audits catalog mappings, not live capture of every item.',
        'The JSON companion records every item, property slot, parameter and classification.',
        '',
        '| Classification | Properties |',
        '| --- | ---: |',
    ]
    lines += [f'| {key} | {value} |' for key, value in sorted(audit['property_counts'].items())]
    lines += [
        '',
        'Min/Max fields can describe damage endpoints, proc chance/skill level, or charge',
        'encodings; unequal fields alone do not establish a variable roll. Review categories',
        'remain explicit instead of claiming complete coverage. Conditional set bonuses need',
        'active-set evidence. Base defense currently requires equal base/total captures and',
        'non-ethereal armor with no intrinsic defense modifiers; enhanced/ethereal/upgraded',
        'defense totals and base weapon damage rolls are not fully reconstructed.',
        '',
        '## Uncovered variable properties or encodings',
        '',
        '| Property | Items |',
        '| --- | --- |',
    ]
    missing = {}
    for item in audit['items']:
        for prop in item['properties']:
            if prop['status'] in ('uncovered_variable_or_encoding', 'encoded_property_review'):
                missing.setdefault(prop['property'], set()).add(item['name'])
    lines += [f'| {code} | {", ".join(sorted(names))} |' for code, names in sorted(missing.items())]
    lines += ['', 'Regenerate offline:', '```sh', 'uv run --offline python -m pricing.knowledge.range_audit', '```', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    audit = audit_ranges(args.root)
    (args.root / 'pricing/data/unique-set-range-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    (args.root / 'inventory_tracking/items/data/RANGE_COVERAGE.md').write_text(render_audit(audit))
    print(json.dumps({'items': audit['item_count'], 'properties': audit['property_counts']}, indent=2))


if __name__ == '__main__':
    main()
