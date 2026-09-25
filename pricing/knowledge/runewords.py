"""Publish an offline runeword census joining definitions, demand and market coverage."""

import json
from collections import Counter
from pathlib import Path

from pricing.knowledge.refresh import atomic_json


def build(root):
    directory = Path(root) / 'pricing/data'
    definitions = json.loads((directory / 'appraisal-definitions.json').read_text())['rows']
    demand = json.loads((directory / 'wp-a-runewords.json').read_text())
    market = Counter()
    for line in (directory / 'appraisal-market.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row.get('scope_status') == 'verified':
            market[row['name']] += 1
    rows = []
    for definition in definitions:
        if definition.get('rarity') != 'runeword':
            continue
        name = definition['name']
        rows.append(
            {
                'kind': 'runeword_profile',
                'name': name,
                'rarity': 'runeword',
                'details': {
                    'definition': definition,
                    'demand': demand.get(name, {}),
                    'variable_stats': {
                        k: v for k, v in definition.get('roll_ranges', {}).items() if v['min'] != v['max']
                    },
                    'scoped_observations': market[name],
                    'price_coverage': 'observations_require_variant_matching' if market[name] else 'no_cached_listings',
                    'comparison_dimensions': [
                        'runeword',
                        'base_code',
                        'ethereal',
                        'sockets',
                        'complete rolled properties',
                        'defense',
                        'inherent skills/resistances',
                    ],
                    'demand_source': 'pricing/data/wp-a-runewords.json',
                },
            }
        )
    return {
        'schema_version': 1,
        'rows': rows,
        'coverage': {
            'definitions': len(rows),
            'with_demand': sum(bool(r['details']['demand']) for r in rows),
            'with_scoped_listings': sum(bool(r['details']['scoped_observations']) for r in rows),
        },
    }


def main():
    root = Path(__file__).resolve().parents[2]
    report = build(root)
    atomic_json(root / 'pricing/data/appraisal-runewords.json', report)
    print(json.dumps(report['coverage']))


if __name__ == '__main__':
    main()
