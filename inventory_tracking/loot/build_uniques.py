"""Regenerate loot/data/uniques.json: the uniques and set items each base item can be, with their asks.

Asks come from pricing/data/wp-i-uniques-misc.json (Traderie, Softcore / Non-Ladder / PC / RotW,
dated in its _meta): `low` and `high` are the lowest and highest per-bucket median ask in Ist, so
`high` is what a good roll asks. Items without pulled asks are listed with nulls, so a base
shows everything it can be. Base class IDs and unique table IDs are the item decoder's.
Run: uv run --offline python -m inventory_tracking.loot.build_uniques
"""

import json
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from inventory_tracking.reports import publish


PRICES = Path('pricing/data/wp-i-uniques-misc.json')
OUTPUT = Path(__file__).parent / 'data' / 'uniques.json'


TABLES = {'uniques': 'unique', 'sets': 'set'}  # ask table type -> decoder identity table


def candidates(prices: dict, kind: str) -> dict[str, list]:
    """Base code -> the spawnable items of one identity table on it, with their asks."""
    asks = {}
    for row in prices.values():
        if row.get('type') != kind:
            continue
        medians = [b['median_ist'] for b in row.get('buckets', {}).values() if b.get('median_ist') is not None]
        if medians:
            asks[row['name']] = (min(medians), max(medians))
    by_code: dict[str, list] = {}
    for table_id, item in metadata()['identities'][TABLES[kind]].items():
        if item['game_definition'].get('spawnable') == 0:
            continue
        low, high = asks.get(item['name'], (None, None))
        for code in item['base_codes']:
            by_code.setdefault(code, []).append({'id': int(table_id), 'name': item['name'], 'low': low, 'high': high})
    return by_code


def build(prices_path: Path) -> dict:
    prices = json.loads(prices_path.read_text())
    uniques, sets = candidates(prices, 'uniques'), candidates(prices, 'sets')
    bases = {}
    for class_id, base in metadata()['bases'].items():
        row = {
            'code': base['code'],
            'name': base['name'],
            'uniques': uniques.get(base['code'], []),
            'sets': sets.get(base['code'], []),
        }
        if any(item['high'] is not None for item in row['uniques'] + row['sets']):
            bases[class_id] = row
    return {
        'source': f'{prices_path} asks joined with the item decoder metadata',
        'date': prices['_meta']['date'],
        'unit': 'Ist = 1, median asks per roll bucket',
        'bases': bases,
    }


def main():
    publish(OUTPUT, build(PRICES))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
