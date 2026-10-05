"""Compare scoped page-zero snapshots; disappearance is not a confirmed sale.

Unfetched boards provide no evidence. A full new page can push old listings off
page zero, so its missing IDs are reported separately from uncensored absence.
"""

import argparse
import json
import re
from collections import defaultdict
from statistics import median

from pricing.triage.bands import eligible, instant


def price_median(rows):
    sellers = {}
    for row in rows:
        price, seller = row.get('ask_ist'), row.get('seller_id')
        if type(price) in (int, float) and price > 0 and seller:
            sellers[seller] = min(sellers.get(seller, price), price)
    return median(sellers.values()) if sellers else None


def compare(before, after, cohort_key):
    groups = defaultdict(lambda: {'old': {}, 'new': {}, 'gone': {}, 'uncensored': set(), 'hours': []})
    invalid = []
    for board in before.keys() & after.keys():
        old, new = before[board], after[board]
        start, end = instant(old.get('observed_at')), instant(new.get('observed_at'))
        if start is None or end is None or end <= start:
            invalid.append(board)
            continue
        new_ids = set(map(str, new['all_ids']))
        touched = set()
        for row in old['rows']:
            key = cohort_key(row)
            group = groups[key]
            identity = str(row['listing_id'])
            group['old'][identity] = row
            touched.add(key)
            if identity not in new_ids:
                group['gone'][identity] = row
                if not new['full_page']:
                    group['uncensored'].add(identity)
        for row in new['rows']:
            key = cohort_key(row)
            groups[key]['new'][str(row['listing_id'])] = row
            touched.add(key)
        for key in touched:
            groups[key]['hours'].append((end - start).total_seconds() / 3600)
    cohorts = {}
    for key, group in sorted(groups.items()):
        old, new, gone = group['old'], group['new'], group['gone']
        old_sellers = {str(r['seller_id']) for r in old.values() if r.get('seller_id')}
        new_sellers = {str(r['seller_id']) for r in new.values() if r.get('seller_id')}
        cohorts[key] = {
            'previous_listings': len(old),
            'current_listings': len(new),
            'disappeared': len(gone),
            'disappeared_share': len(gone) / len(old) if old else None,
            'uncensored_disappeared': len(group['uncensored']),
            'censored_disappeared': len(gone) - len(group['uncensored']),
            'new_sellers': len(new_sellers - old_sellers),
            'previous_sellers': len(old_sellers),
            'current_sellers': len(new_sellers),
            'gone_median_ist': price_median(gone.values()),
            'retained_median_ist': price_median(r for identity, r in old.items() if identity not in gone),
            'minimum_interval_hours': min(group['hours']),
            'maximum_interval_hours': max(group['hours']),
        }
    return {
        'cohorts': cohorts,
        'compared_boards': len(before.keys() & after.keys()) - len(invalid),
        'unobserved_boards': sorted(before.keys() - after.keys()),
        'invalid_intervals': sorted(invalid),
        'interpretation': (
            'Page-zero listing disappearance, not confirmed sales; full-page absence may be displacement.'
        ),
    }


def read_snapshot(directory, catalog, currencies, *, normalization_cache=None):
    from pricing.knowledge.market import normalize_listing
    from pricing.triage.listing_defaults import normalize

    boards = {}
    for path in sorted(directory.glob('*-p0.json')):
        identity = path.name.removesuffix('-p0.json')
        item = catalog.get(identity)
        if item is None:
            continue
        raw_bytes = path.read_bytes()
        payload = json.loads(raw_bytes)
        if not isinstance(payload.get('listings'), list):
            continue  # A cached error is not an exhausted page.
        raw = payload['listings']
        cached = (normalization_cache or {}).get(path.resolve())
        reused = cached[1] if cached is not None and cached[0] == raw_bytes else None
        rows = []
        if reused is None:
            reused = [
                normalize_listing(
                    row,
                    name=item['name'],
                    category=item['type'],
                    source=str(path),
                    observed_at=payload.get('_pulled_at'),
                    currencies=currencies,
                )
                for row in raw
                if str(row.get('item_id')) == identity
            ]
        for row in reused:
            normalized = normalize(row | {'source': str(path)})
            if eligible(normalized):
                rows.append(normalized)
        boards[identity] = {
            'rows': rows,
            'all_ids': [str(row['id']) for row in raw],
            'full_page': len(raw) >= 50,
            'observed_at': payload.get('_pulled_at'),
        }
    return boards


def report(before, after, tables, root, *, normalization_cache=None):
    from pricing.knowledge.artifacts import artifact_snapshot
    from pricing.knowledge.assessment.mechanics.base_tiers import CATALOG

    with artifact_snapshot([CATALOG]):
        return _report(before, after, tables, root, normalization_cache=normalization_cache)


def _report(before, after, tables, root, *, normalization_cache=None):
    from pricing.triage.adapters import from_listing
    from pricing.triage.base_socket_inference import apply
    from pricing.triage.engine import assess, variant_name_band
    from pricing.triage.listing_scores import cohort_key

    def identity(row):
        row = apply(row, tables.get('base_socket_inferences', {}))
        item = from_listing(row)
        result = assess(item, tables)
        band = variant_name_band(item, tables)
        return cohort_key(item, result, band, tables)

    catalog = json.loads((root / 'pricing/data/appraisal-traderie-catalog.json').read_text())['items']
    catalog = {str(item['id']): item for item in catalog}
    ladder = json.loads((root / 'pricing/data/wp-f-ladder.json').read_text())
    currencies = {k.lower(): v['ist'] for k, v in ladder.items() if isinstance(v, dict) and 'ist' in v}
    result = compare(
        read_snapshot(before, catalog, currencies, normalization_cache=normalization_cache),
        read_snapshot(after, catalog, currencies, normalization_cache=normalization_cache),
        identity,
    )
    from pricing.triage.buyers import cached_report

    return result | {
        'before': str(before),
        'after': str(after),
        'buyers': cached_report(root, catalog, identity),
    }


def latest_report(tables, root, *, normalization_cache=None):
    directories = sorted(
        p for p in (root / 'pricing/raw/traderie').glob('pull-*') if p.is_dir() and re.fullmatch(r'pull-\d{8}', p.name)
    )
    if len(directories) < 2:
        return None
    return report(directories[-2], directories[-1], tables, root, normalization_cache=normalization_cache)


def main():
    from pathlib import Path

    from pricing.knowledge.refresh import atomic_json
    from pricing.triage.build import ROOT
    from pricing.triage.engine import Tables

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    args = parser.parse_args()
    result = report(args.before, args.after, Tables().load(), ROOT)
    path = ROOT / 'inventory_tracking/corpus/data/score-listings.json'
    score = json.loads(path.read_text()) if path.exists() else {}
    score['turnover'] = result
    atomic_json(path, score)
    print(
        json.dumps({k: v for k, v in result.items() if k != 'cohorts'} | {'cohorts': len(result['cohorts'])}, indent=2)
    )


if __name__ == '__main__':
    main()
