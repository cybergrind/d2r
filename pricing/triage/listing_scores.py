"""Seller votes for replay, with listing counts retained as secondary evidence."""

import json
import math
from collections import Counter

from pricing.triage.patterns import matched_patterns
from pricing.triage.rule_index import candidates


def evidence_backed_check(item, result, tables):
    """Attention needs a matched quote or reviewed demand, not missing information."""
    if result['verdict'] != 'check':
        return False
    if item.get('category') == 'affixed_unknown':
        from pricing.triage.unknown_affixed import review_pattern

        return bool(review_pattern(item, tables))
    rows = candidates(item, tables['pattern_index']) if 'pattern_index' in tables else tables['rules']['rows']
    if matched_patterns(item, rows, socket_preparation=result.get('preparation')):
        return True
    reference = result.get('reference_band') or {}
    price = reference.get('q1_ist')
    if result.get('sale_mode') == 'accumulate' and type(price) in (int, float):
        price *= reference.get('quantity', 1)
    priced = type(price) in (int, float) and math.isfinite(price) and price >= tables['rules']['keep_ist']
    if priced and reference.get('sellers', 0) > 0:
        if result.get('bucket') is not None and result['bucket'] == reference.get('bucket'):
            return True
        if result.get('sale_mode') == 'accumulate':
            return True
        deciding = (result.get('roll_comparison') or {}).get('deciding', {})
        if deciding and all(
            type(item.get('properties', {}).get(key)) in (int, float)
            and math.isfinite(item['properties'][key])
            and spec.get('min', math.inf) <= item['properties'][key] <= spec.get('max', -math.inf)
            for key, spec in deciding.items()
        ):
            return True
    return False


def cohort_key(item, result, named_cohort, tables):
    category = item['category']
    identity = [category, item.get('name'), item.get('ethereal')]
    if category in ('rare', 'magic', 'crafted'):
        rows = candidates(item, tables['pattern_index']) if 'pattern_index' in tables else tables['rules']['rows']
        patterns = matched_patterns(item, rows, socket_preparation=result.get('preparation'))
        # The full paid pattern identifies a market, not the exact secondary rolls.
        signatures = sorted(json.dumps({**r, **r['pattern']}, sort_keys=True) for r in patterns)
        if not signatures and result.get('band'):
            signatures = [result['band'].get('bucket')]
        identity = [category, item.get('family') or item.get('name'), item.get('ethereal'), signatures]
    else:
        band = named_cohort if category in ('uniques', 'sets', 'runewords') else result.get('band')
        identity += [band.get('bucket') if band else None]
        if not band:
            identity += [item.get('base_code'), item.get('sockets'), item.get('socket_contents')]
    return json.dumps(identity, sort_keys=True)


def summarize(observations):
    categories, types = {}, {}
    for category, key, tally in observations:
        categories.setdefault(category, Counter()).update(tally)
        types.setdefault(key, Counter()).update(tally)

    def rates(tally):
        return {
            **tally,
            'valuable': tally['valuable'],
            'recall': tally['flagged_valuable'] / tally['valuable'] if tally['valuable'] else None,
            'sell_recall': tally['sell_flagged_valuable'] / tally['valuable'] if tally['valuable'] else None,
            'recall_without_unmeasured': (tally['flagged_valuable'] - tally['demand_unmeasured_valuable'])
            / tally['valuable']
            if tally['valuable']
            else None,
            'cheap_false_positive_rate': tally['flagged_cheap'] / tally['cheap'] if tally['cheap'] else None,
            'cheap_check_rate': tally['checks_cheap'] / tally['cheap'] if tally['cheap'] else None,
        }

    return {
        'overall': rates(sum(categories.values(), Counter())),
        'categories': {k: rates(v) for k, v in sorted(categories.items())},
        'per_type': {k: rates(v) for k, v in sorted(types.items())},
    }
