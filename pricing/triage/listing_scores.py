"""Seller votes for replay, with listing counts retained as secondary evidence."""

import json
from collections import Counter

from pricing.triage.patterns import matched_patterns
from pricing.triage.rule_index import candidates


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
            'cheap_false_positive_rate': tally['flagged_cheap'] / tally['cheap'] if tally['cheap'] else None,
            'cheap_check_rate': tally['checks_cheap'] / tally['cheap'] if tally['cheap'] else None,
        }

    return {
        'overall': rates(sum(categories.values(), Counter())),
        'categories': {k: rates(v) for k, v in sorted(categories.items())},
        'per_type': {k: rates(v) for k, v in sorted(types.items())},
    }
