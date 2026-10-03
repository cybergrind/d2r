"""Build triage bands from existing offline sources; never collect market pages."""

import json
from collections import Counter
from pathlib import Path

from pricing.knowledge.market import normalize_listing
from pricing.triage.bands import build_bands


ROOT = Path(__file__).resolve().parents[2]


def market_rows(root=ROOT):
    data = root / 'pricing/data'
    catalog = json.loads((data / 'appraisal-traderie-catalog.json').read_text())['items']
    by_id = {str(r['id']): r for r in catalog}
    ladder = json.loads((data / 'wp-f-ladder.json').read_text())
    currencies = {k.lower(): v['ist'] for k, v in ladder.items() if isinstance(v, dict) and 'ist' in v}
    with (data / 'appraisal-market.jsonl').open() as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    commodity = data / 'appraisal-commodity-market.json'
    if commodity.exists():
        rows.extend(json.loads(commodity.read_text())['rows'])
    for path in sorted((root / 'pricing/raw/traderie').glob('pull-*/*-p*.json')):
        cached = json.loads(path.read_text())
        item = by_id.get(path.name.split('-p')[0])
        if not item:
            continue
        for row in cached.get('listings', []):
            if str(row.get('item_id')) != str(item['id']):
                continue
            rows.append(
                normalize_listing(
                    row,
                    name=item['name'],
                    category=item['type'],
                    source=str(path.relative_to(root)),
                    observed_at=cached.get('_pulled_at'),
                    currencies=currencies,
                )
            )
    return rows, catalog


def main():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.refresh import atomic_json
    from pricing.triage.analyze_rolls import analyze
    from pricing.triage.compiled_rolls import compile_model

    rows, catalog = market_rows()
    rules = json.loads((ROOT / 'pricing/data/triage/rules.json').read_text())
    document = build_bands(rows, catalog, rules=rules['rows'], policies=rules.get('policies', []))
    definitions = json.loads((ROOT / 'pricing/data/appraisal-definitions.json').read_text())['rows']
    reports = analyze(rows, definitions, metadata())
    from pricing.triage.bands import latest_rows

    unique_rows = latest_rows(rows)
    document['roll_models'] = [model for report in reports if (model := compile_model(report, unique_rows))]
    output = ROOT / 'pricing/data/triage'
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / 'bands.json', document)
    print(
        json.dumps(
            {
                'bands': len(document['bands']),
                'roll_models': len(document['roll_models']),
                'priced': sum(b['median_ist'] is not None for b in document['bands']),
                'liquidity': dict(Counter(b['liquidity'] for b in document['bands'])),
            }
        )
    )


if __name__ == '__main__':
    main()
