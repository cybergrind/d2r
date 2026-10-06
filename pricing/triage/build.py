"""Build triage bands from existing offline sources; never collect market pages."""

import json
from collections import Counter
from pathlib import Path

from pricing.knowledge.artifacts import artifact_snapshot
from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG as BASE_CATALOG
from pricing.knowledge.market import normalize_listing
from pricing.triage.bands import build_bands
from pricing.triage.listing_defaults import normalize as listing_defaults


ROOT = Path(__file__).resolve().parents[2]


def market_rows(root=ROOT, *, normalization_cache=None):
    # Immutable bytes for this batch only: avoid re-reading and hashing the
    # same catalog for every listing while seeing changes on the next run.
    with artifact_snapshot([BASE_CATALOG]):
        return _market_rows(root, normalization_cache=normalization_cache)


def _market_rows(root, *, normalization_cache=None):
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
        raw_bytes = path.read_bytes()
        cached = json.loads(raw_bytes)
        item = by_id.get(path.name.split('-p')[0])
        if not item:
            continue
        page_rows = []
        for row in cached.get('listings', []):
            if str(row.get('item_id')) != str(item['id']):
                continue
            page_rows.append(
                normalize_listing(
                    row,
                    name=item['name'],
                    category=item['type'],
                    source=str(path.relative_to(root)),
                    observed_at=cached.get('_pulled_at'),
                    currencies=currencies,
                )
            )
        rows.extend(page_rows)
        if normalization_cache is not None:
            # Replay-local reuse only. Original bytes detect concurrent collector
            # updates; cache before gem/stock processing to preserve snapshot semantics.
            normalization_cache[path.resolve()] = (raw_bytes, page_rows)
    from pricing.triage.currencies import apply_gem_quotes
    from pricing.triage.stock_evidence import restore

    return [listing_defaults(row) for row in apply_gem_quotes(restore(rows, root), currencies)], catalog


def main():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.refresh import atomic_json
    from pricing.triage.analyze_rolls import analyze, guide_rolls
    from pricing.triage.compiled_rolls import compile_model

    normalization_cache = {}
    rows, catalog = market_rows(normalization_cache=normalization_cache)
    from pricing.triage.base_socket_inference import apply, compile_inferences

    utility = json.loads((ROOT / 'pricing/data/appraisal-utility.json').read_text())['rows']
    socket_inferences = compile_inferences(rows, utility)
    rows = [listing_defaults(apply(row, socket_inferences)) for row in rows]
    rules = json.loads((ROOT / 'pricing/data/triage/rules.json').read_text())
    document = build_bands(rows, catalog, rules=rules['rows'], policies=rules.get('policies', []))
    document['base_socket_inferences'] = socket_inferences
    from pricing.triage.demand import compile_demand

    demand = json.loads((ROOT / 'pricing/data/appraisal-demand.json').read_text())['rows']
    watches = json.loads((ROOT / 'pricing/data/appraisal-value-watch.json').read_text())['rows']
    document['demand'] = compile_demand(demand, watches)
    from pricing.triage.base_demand import compile_bases

    recommended_bases = json.loads((ROOT / 'pricing/data/wp-a-bases.json').read_text())
    document['demand'].update(compile_bases(recommended_bases, utility, document['demand']))
    definitions = json.loads((ROOT / 'pricing/data/appraisal-definitions.json').read_text())['rows']
    guide_rules = guide_rolls((ROOT / 'guides/pricing.html').read_text(), 'guides/pricing.html#s8')
    reports = analyze(rows, definitions, metadata(), coarse=True, guide_rules=guide_rules)
    from pricing.triage.bands import latest_rows

    unique_rows = latest_rows(rows)
    document['roll_models'] = [
        model for report in reports if (model := compile_model(report, unique_rows, require_supported_split=True))
    ]
    from pricing.triage.engine import prepare_tables
    from pricing.triage.market_demand import compile_evidence
    from pricing.triage.turnover import latest_report

    own = json.loads((ROOT / 'pricing/data/triage/own.json').read_text())
    tables = prepare_tables(document, rules, own)
    document['market_demand'] = compile_evidence(latest_report(tables, ROOT, normalization_cache=normalization_cache))
    document['learned_patterns'] = []
    output = ROOT / 'pricing/data/triage'
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / 'bands.json', document)
    print(
        json.dumps(
            {
                'bands': len(document['bands']),
                'learned_patterns': len(document['learned_patterns']),
                'roll_models': len(document['roll_models']),
                'priced': sum(b['median_ist'] is not None for b in document['bands']),
                'liquidity': dict(Counter(b['liquidity'] for b in document['bands'])),
            }
        )
    )


if __name__ == '__main__':
    main()
