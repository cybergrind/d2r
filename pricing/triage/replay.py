"""Both triage score reports from local data, without detail-engine appraisal."""

import json
import time
from collections import Counter
from statistics import median

from inventory_tracking.corpus.build import DATA, RUNS, merge
from inventory_tracking.corpus.score import load, score
from pricing.triage.adapters import from_drop, from_listing
from pricing.triage.analyze_rolls import analyze
from pricing.triage.bands import eligible, latest_rows
from pricing.triage.build import ROOT, market_rows
from pricing.triage.commodity_lots import sale_value
from pricing.triage.engine import Tables, assess, variant_name_band
from pricing.triage.roll_comparisons import validation_summary


def listing_score(rows, tables):
    from pricing.triage.base_socket_inference import apply
    from pricing.triage.listing_scores import cohort_key, summarize
    from pricing.triage.miss_causes import MissCauses

    observations = []
    sellers = {}
    missing_seller = 0
    excluded = Counter()
    excluded_sellers = set()
    misses = MissCauses()
    cohort_verdicts = {}
    for row in latest_rows(rows):
        price = row.get('ask_ist')
        if not eligible(row) or type(price) not in (int, float) or price <= 0:
            continue
        row = apply(row, tables.get('base_socket_inferences', {}))
        item = from_listing(row)
        if item['category'] == 'base' and item.get('sockets') is None:
            excluded['base_missing_sockets'] += 1
            excluded['valuable_base_missing_sockets'] += price >= tables['rules']['keep_ist']
            if row.get('seller_id'):
                excluded_sellers.add(str(row['seller_id']))
            continue
        price = sale_value(item, price)
        category = item['category']
        result = assess(item, tables)
        verdict = result['verdict']
        flag = verdict in ('sell', 'slow')
        attention = flag or (category in ('rare', 'magic', 'crafted') and verdict == 'check')
        key = f'{category}/{item.get("family") or item.get("name")}'
        named = category in ('uniques', 'sets', 'runewords')
        cohort = variant_name_band(item, tables) if named else None
        cohort_price = (cohort or {}).get('q1_ist') if named else price
        valuable = cohort_price is not None and cohort_price >= tables['rules']['keep_ist']
        cheap = price < tables['rules']['keep_ist'] / 4
        tally = Counter(
            {
                'priced': 1,
                'checks': int(verdict == 'check'),
                'unpriced_cohort': int(named and cohort_price is None),
                'asks_above_cheap_cohort': int(
                    named and cohort_price is not None and cohort_price < tables['rules']['keep_ist'] <= price
                ),
                'valuable': int(valuable),
                'flagged_valuable': int(valuable and attention),
                'sell_flagged_valuable': int(valuable and flag),
                'checks_valuable': int(valuable and verdict == 'check'),
                'cheap': int(cheap),
                'flagged_cheap': int(cheap and flag),
                'checks_cheap': int(cheap and verdict == 'check'),
            }
        )
        observation = category, key, tally
        observations.append(observation)
        miss = misses.add(row, item, result, tables) if valuable and not attention else None
        if not row.get('seller_id'):
            missing_seller += 1
            continue
        market_cohort = cohort_key(item, result, cohort, tables)
        cohort_verdicts.setdefault(market_cohort, set()).add(verdict)
        identity = str(row['seller_id']), market_cohort
        rank = price, str(row['listing_id'])
        if identity not in sellers or rank < sellers[identity][0]:
            sellers[identity] = rank, observation, miss
    return {
        **summarize([o for _, o, _ in sellers.values()]),
        'miss_causes': misses.report([miss for _, _, miss in sellers.values()]),
        'weighting': 'one vote per seller per cohort or paid pattern; lowest ask wins',
        'missing_seller_listings': missing_seller,
        'excluded_listings': dict(excluded),
        'excluded_distinct_sellers': len(excluded_sellers),
        'per_listing': summarize(observations),
        'cohort_verdicts': {key: sorted(values) for key, values in sorted(cohort_verdicts.items())},
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
    from pricing.triage.guide_cases import build_cases, evaluate

    guide_score = evaluate(build_cases(), lambda item: assess(item, tables))
    atomic_json(DATA / 'score-guides.json', guide_score)
    summary = {'explicit_regressions': score(results, labels), 'guide_cases': guide_score['groups']}
    rarity_counts = {}
    for result in results:
        rarity_counts.setdefault(result.get('rarity', 'unknown'), Counter())[result['verdict']] += 1
    summary['check_share_by_rarity'] = {
        rarity: {
            'items': sum(counts.values()),
            'checks': counts['check'],
            'share': counts['check'] / sum(counts.values()),
        }
        for rarity, counts in sorted(rarity_counts.items())
    }
    named = sum((counts for rarity, counts in rarity_counts.items() if rarity in ('unique', 'set')), Counter())
    summary['named_check_share'] = named['check'] / sum(named.values()) if named else None
    baseline = json.loads((DATA / 'score-legacy-baseline-20261003.json').read_text())
    comparison = compare_types(items, results, baseline['results'], keep_ist=tables['rules']['keep_ist'])
    atomic_json(DATA / 'score-triage.json', {'summary': summary, 'results': results, 'per_type': comparison})
    normalization_cache = {}
    rows, _ = market_rows(normalization_cache=normalization_cache)
    listing = listing_score(rows, tables)
    from pricing.triage.demand import cohorts_without_demand

    listing['sub_ist_without_demand'] = cohorts_without_demand(tables)
    definitions = json.loads((ROOT / 'pricing/data/appraisal-definitions.json').read_text())['rows']
    models = analyze(rows, definitions, metadata(), coarse=True)
    listing['roll_validation'] = {
        'models': models,
        'drafts': len(models),
        'beat_name_median': sum(r['validation']['use_roll_model'] for r in models),
        'aggregate': validation_summary(models),
        'compiled_comparisons': len(tables.get('roll_models', [])),
    }
    from pricing.triage.turnover import latest_report

    listing['turnover'] = latest_report(tables, ROOT, normalization_cache=normalization_cache)
    from pricing.triage.market_demand import agreement

    listing['demand_agreement'] = agreement(listing['cohort_verdicts'], listing['turnover'])
    atomic_json(DATA / 'score-listings.json', listing)
    print(
        json.dumps(
            {
                'corpus': {
                    'items': len(results),
                    'verdicts': dict(Counter(r['verdict'] for r in results)),
                    'bands': sum(r['band'] is not None and r['band']['median_ist'] is not None for r in results),
                    'summary': summary,
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
