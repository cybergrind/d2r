"""Both triage score reports from local data, without detail-engine appraisal."""

import json
import time
from collections import Counter
from statistics import median

from inventory_tracking.corpus.build import DATA
from inventory_tracking.corpus.score import load, score
from pricing.triage.adapters import from_drop, from_listing
from pricing.triage.analyze_rolls import analyze
from pricing.triage.bands import eligible, latest_rows
from pricing.triage.build import ROOT, market_rows
from pricing.triage.engine import Tables, assess


def listing_score(rows, tables):
    counts = {}
    for row in latest_rows(rows):
        price = row.get('ask_ist')
        if not eligible(row) or type(price) not in (int, float) or price <= 0:
            continue
        item = from_listing(row)
        category = item['category']
        tally = counts.setdefault(category, Counter())
        verdict = assess(item, tables)['verdict']
        flag = verdict in ('sell', 'slow')
        tally['priced'] += 1
        tally['checks'] += verdict == 'check'
        if price >= tables['rules']['keep_ist']:
            tally['valuable'] += 1
            tally['flagged_valuable'] += flag
            tally['checks_valuable'] += verdict == 'check'
        elif price < tables['rules']['keep_ist'] / 4:
            tally['cheap'] += 1
            tally['flagged_cheap'] += flag
            tally['checks_cheap'] += verdict == 'check'

    def summarize(tally):
        return {
            **tally,
            'recall': tally['flagged_valuable'] / tally['valuable'] if tally['valuable'] else None,
            'cheap_false_positive_rate': tally['flagged_cheap'] / tally['cheap'] if tally['cheap'] else None,
        }

    return {
        'overall': summarize(sum(counts.values(), Counter())),
        'categories': {k: summarize(v) for k, v in sorted(counts.items())},
    }


def compare_types(items, results, legacy):
    old = {r['id']: r for r in legacy}
    new = {r['id']: r for r in results}
    groups = {}
    for row in items:
        item = from_drop(row['observation'])
        key = f'{item["category"]}/{item.get("family") or item.get("name")}'
        group = groups.setdefault(key, {'legacy': Counter(), 'triage': Counter(), 'lost_attention': []})
        before, after = old.get(row['id']), new.get(row['id'])
        if before is None or after is None:
            continue
        group['legacy'][before['verdict']] += 1
        group['triage'][after['verdict']] += 1
        if before['verdict'] in ('keep', 'check') and after['verdict'] == 'vendor':
            group['lost_attention'].append({'id': row['id'], 'name': item['name']})
    return dict(sorted(groups.items()))


def main():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.refresh import atomic_json

    started = time.perf_counter()
    tables = Tables().load()
    items, labels = load(DATA)
    results, timings = [], []
    for row in items:
        before = time.perf_counter()
        result = assess(from_drop(row['observation']), tables)
        timings.append((time.perf_counter() - before) * 1000)
        item = row['observation']['item']
        results.append({'id': row['id'], 'name': item.get('name'), 'rarity': item.get('rarity'), **result})
    summary = score(results, labels)
    baseline = json.loads((DATA / 'score-legacy-baseline-20261003.json').read_text())
    comparison = compare_types(items, results, baseline['results'])
    atomic_json(DATA / 'score-triage.json', {'summary': summary, 'results': results, 'per_type': comparison})
    rows, _ = market_rows()
    listing = listing_score(rows, tables)
    definitions = json.loads((ROOT / 'pricing/data/appraisal-definitions.json').read_text())['rows']
    models = analyze(rows, definitions, metadata())
    listing['roll_validation'] = {
        'models': models,
        'drafts': len(models),
        'beat_name_median': sum(r['validation']['use_roll_model'] for r in models),
        'live_enabled': False,
    }
    atomic_json(DATA / 'score-listings.json', listing)
    print(
        json.dumps(
            {
                'corpus': {
                    'items': len(results),
                    'verdicts': dict(Counter(r['verdict'] for r in results)),
                    'bands': sum(r['band'] is not None and r['band']['median_ist'] is not None for r in results),
                    'labels': summary,
                },
                'listings': listing,
                'per_type': comparison,
                'timing_ms': {'first': timings[0], 'median': median(timings), 'max': max(timings)},
                'report_seconds': time.perf_counter() - started,
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
