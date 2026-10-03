"""Both triage score reports from local data, without detail-engine appraisal."""

import json
import time
from collections import Counter
from statistics import median

from inventory_tracking.corpus.build import DATA, RUNS, label_page, merge
from inventory_tracking.corpus.score import load, score
from pricing.triage.adapters import from_drop, from_listing
from pricing.triage.analyze_rolls import analyze
from pricing.triage.bands import eligible, latest_rows
from pricing.triage.build import ROOT, market_rows
from pricing.triage.commodity_lots import sale_value
from pricing.triage.engine import Tables, assess, variant_name_band
from pricing.triage.roll_comparisons import validation_summary


def listing_score(rows, tables):
    counts = {}
    types = {}
    for row in latest_rows(rows):
        price = row.get('ask_ist')
        if not eligible(row) or type(price) not in (int, float) or price <= 0:
            continue
        item = from_listing(row)
        price = sale_value(item, price)
        category = item['category']
        verdict = assess(item, tables)['verdict']
        flag = verdict in ('sell', 'slow')
        attention = flag or (category in ('rare', 'magic', 'crafted') and verdict == 'check')
        key = f'{category}/{item.get("family") or item.get("name")}'
        named = category in ('uniques', 'sets', 'runewords')
        cohort_price = (variant_name_band(item, tables) or {}).get('q1_ist') if named else price
        valuable = cohort_price is not None and cohort_price >= tables['rules']['keep_ist']
        for tally in (counts.setdefault(category, Counter()), types.setdefault(key, Counter())):
            tally['priced'] += 1
            tally['checks'] += verdict == 'check'
            if named and cohort_price is None:
                tally['unpriced_cohort'] += 1
            if named and cohort_price is not None and cohort_price < tables['rules']['keep_ist'] <= price:
                tally['asks_above_cheap_cohort'] += 1
            if valuable:
                tally['valuable'] += 1
                tally['flagged_valuable'] += attention
                tally['sell_flagged_valuable'] += flag
                tally['checks_valuable'] += verdict == 'check'
            if price < tables['rules']['keep_ist'] / 4:
                tally['cheap'] += 1
                tally['flagged_cheap'] += flag
                tally['checks_cheap'] += verdict == 'check'

    def summarize(tally):
        return {
            **tally,
            'valuable': tally['valuable'],
            'recall': tally['flagged_valuable'] / tally['valuable'] if tally['valuable'] else None,
            'sell_recall': tally['sell_flagged_valuable'] / tally['valuable'] if tally['valuable'] else None,
            'cheap_false_positive_rate': tally['flagged_cheap'] / tally['cheap'] if tally['cheap'] else None,
            'cheap_check_rate': tally['checks_cheap'] / tally['cheap'] if tally['cheap'] else None,
        }

    return {
        'overall': summarize(sum(counts.values(), Counter())),
        'categories': {k: summarize(v) for k, v in sorted(counts.items())},
        'per_type': {k: summarize(v) for k, v in sorted(types.items())},
    }


def explained_vendor(item, result, keep_ist):
    if item['category'] not in ('uniques', 'sets', 'runewords'):
        return False
    band = result.get('band') or {}
    price = band.get('q1_ist')
    known = (
        item.get('base_code') is not None
        and (item['category'] == 'sets' or type(item.get('ethereal')) is bool)
        and type(item.get('sockets')) is int
        and item.get('socket_contents') in ('empty', 'filled')
    )
    if known and type(price) in (int, float) and 0 < price < keep_ist and band.get('sellers', 0) >= 3:
        return True
    comparison = result.get('roll_comparison') or {}
    ceiling = comparison.get('upper_bound_ist')
    return known and type(ceiling) in (int, float) and 0 < ceiling < keep_ist


def compare_types(items, results, legacy, *, keep_ist):
    old = {r['id']: r for r in legacy}
    new = {r['id']: r for r in results}
    groups = {}
    for row in items:
        item = from_drop(row['observation'])
        key = f'{item["category"]}/{item.get("family") or item.get("name")}'
        group = groups.setdefault(
            key,
            {
                'legacy': Counter(),
                'triage': Counter(),
                'lost_attention': [],
                'accepted_corrections': [],
                'without_legacy': [],
            },
        )
        before, after = old.get(row['id']), new.get(row['id'])
        if after is None:
            continue
        group['triage'][after['verdict']] += 1
        if before is None:
            group['without_legacy'].append(row['id'])
            continue
        group['legacy'][before['verdict']] += 1
        if before['verdict'] in ('keep', 'check') and after['verdict'] == 'vendor':
            entry = {'id': row['id'], 'name': item['name']}
            if explained_vendor(item, after, keep_ist):
                band = after.get('band') or {}
                group['accepted_corrections'].append(
                    {
                        **entry,
                        'legacy': before['verdict'],
                        'reason': after.get('reason'),
                        'q1_ist': band.get('q1_ist'),
                        'sellers': band.get('sellers'),
                        'upper_bound_ist': (after.get('roll_comparison') or {}).get('upper_bound_ist'),
                    }
                )
            else:
                group['lost_attention'].append(entry)
    return dict(sorted(groups.items()))


def main():
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.refresh import atomic_json

    started = time.perf_counter()
    tables = Tables().load()
    merge(RUNS, DATA)
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
    comparison = compare_types(items, results, baseline['results'], keep_ist=tables['rules']['keep_ist'])
    atomic_json(DATA / 'score-triage.json', {'summary': summary, 'results': results, 'per_type': comparison})
    old = {r['id']: r for r in baseline['results']}
    disputes = sorted(
        r['id']
        for r in results
        if r['verdict'] in ('check', 'sell')
        or (r['verdict'] == 'vendor' and old.get(r['id'], {}).get('verdict') in ('keep', 'check'))
    )
    observations = {r['id']: r['observation'] for r in items}
    (DATA / 'label.html').write_text(label_page(observations, disputes, labels=labels))
    rows, _ = market_rows()
    listing = listing_score(rows, tables)
    definitions = json.loads((ROOT / 'pricing/data/appraisal-definitions.json').read_text())['rows']
    models = analyze(rows, definitions, metadata())
    listing['roll_validation'] = {
        'models': models,
        'drafts': len(models),
        'beat_name_median': sum(r['validation']['use_roll_model'] for r in models),
        'aggregate': validation_summary(models),
        'compiled_comparisons': len(tables.get('roll_models', [])),
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
