"""Regenerate loot/data/uniques.json: the uniques each base item can be, with their asks.

Asks come from pricing/data/wp-i-uniques-misc.json (Traderie, Softcore / Non-Ladder / PC / RotW,
dated in its _meta): `low` and `high` are the lowest and highest per-bucket median ask in Ist, so
`high` is what a good roll asks. Uniques without pulled asks are listed with nulls, so a base
shows every unique it can be. Base class IDs and unique table IDs are the item decoder's.
Run: uv run --offline python -m inventory_tracking.loot.build_uniques
"""

import json
from pathlib import Path

from inventory_tracking.items.metadata import metadata
from inventory_tracking.reports import publish


PRICES = Path('pricing/data/wp-i-uniques-misc.json')
OUTPUT = Path(__file__).parent / 'data' / 'uniques.json'


def build(prices_path: Path) -> dict:
    prices = json.loads(prices_path.read_text())
    asks = {}
    for row in prices.values():
        if row.get('type') != 'uniques':
            continue
        medians = [b['median_ist'] for b in row.get('buckets', {}).values() if b.get('median_ist') is not None]
        if medians:
            asks[row['name']] = (min(medians), max(medians))
    by_code: dict[str, list] = {}
    for table_id, unique in metadata()['identities']['unique'].items():
        if unique['game_definition'].get('spawnable') == 0:
            continue
        low, high = asks.get(unique['name'], (None, None))
        for code in unique['base_codes']:
            by_code.setdefault(code, []).append({'id': int(table_id), 'name': unique['name'], 'low': low, 'high': high})
    bases = {
        class_id: {'code': base['code'], 'name': base['name'], 'uniques': by_code[base['code']]}
        for class_id, base in metadata()['bases'].items()
        if any(unique['high'] is not None for unique in by_code.get(base['code'], ()))
    }
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
