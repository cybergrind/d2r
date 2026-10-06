"""Offline listing-derived combinations; review references, never sale estimates."""

import math
from collections import Counter, defaultdict
from itertools import combinations

from pricing.triage.adapters import AFFIXED, BASE_CONTEXT, from_listing
from pricing.triage.bands import band_for, eligible, latest_rows, timestamp


CONTEXT = BASE_CONTEXT - {'425', '510'}


def derive(rows, property_ids, keep_ist):
    """Learn shared combinations without dropping universally present affixes."""
    from pricing.triage.engine import matches

    groups = defaultdict(list)
    for row in latest_rows(rows):
        if not eligible(row) or row.get('amount') != 1:
            continue
        ask = row.get('ask_ist')
        if type(ask) not in (int, float) or not math.isfinite(ask) or ask <= 0 or not timestamp(row.get('observed_at')):
            continue
        item = from_listing(row)
        if item['category'] not in AFFIXED or not item.get('family'):
            continue
        if type(item.get('ethereal')) is not bool or item.get('socket_contents') != 'empty':
            continue
        if type(item.get('sockets')) is not int or not item.get('base_name'):
            continue
        props = {
            key: value
            for key, value in item['properties'].items()
            if key in property_ids
            and key not in CONTEXT
            and type(value) in (int, float)
            and math.isfinite(value)
            and value > 0
        }
        keys = tuple(sorted(props))
        signatures = {keys} if keys else set()
        for size in (2, 3):
            signatures.update(combinations(keys, size))
        item = item | {'learned_properties': props}
        for signature in signatures:
            key = item['category'], item['family'], item['ethereal'], item['sockets'], signature
            groups[key].append((row, item))
    result = []
    for (category, family, ethereal, sockets, signature), members in sorted(groups.items()):
        paid = [
            (row, item)
            for row, item in members
            if type(row.get('ask_ist')) in (int, float) and row['ask_ist'] >= keep_ist and row.get('seller_id')
        ]
        if len({row['seller_id'] for row, _ in paid}) < 3:
            continue
        shared = set.intersection(*(set(item['learned_properties']) for _, item in paid))
        if shared != set(signature):
            continue
        rule = {
            'category': category,
            'family': family,
            'conditions': {
                'ethereal': ethereal,
                'sockets': sockets,
                'socket_contents': 'empty',
                'base_name': {'in': sorted({item['base_name'] for _, item in paid})},
            },
            'properties': {key: {'min': min(item['properties'][key] for _, item in paid)} for key in signature},
        }
        matched = [row for row, item in members if matches(item, rule)]
        sellers = {}
        for row in matched:
            if row.get('seller_id'):
                seller = str(row['seller_id'])
                sellers[seller] = min(sellers.get(seller, math.inf), row['ask_ist'])
        valuable = sum(value >= keep_ist for value in sellers.values())
        if valuable < 3:
            continue
        reference = band_for(category, family, matched)
        supporters = [
            {key: row.get(key) for key in ('seller_id', 'ask_ist', 'observed_at', 'listing_updated_at', 'prices')}
            | {'properties': {key: item['properties'][key] for key in signature}}
            for row, item in members
            if matches(item, rule)
        ]
        rule.update(reference_band=reference, valuable_sellers=valuable, supporters=supporters, keep_ist=keep_ist)
        result.append(rule)
    # Largest families first; broadest supported combinations first within them.
    family_votes = Counter()
    for rule in result:
        family_votes[rule['category'], rule['family']] = max(
            family_votes[rule['category'], rule['family']], rule['valuable_sellers']
        )
    return sorted(
        result,
        key=lambda r: (
            -family_votes[r['category'], r['family']],
            -r['valuable_sellers'],
            r['category'],
            r['family'],
            tuple(r['properties']),
        ),
    )


def guard(patterns, corpus, verdicts, limit=0.08, *, negatives=()):
    """Reject a whole pattern if cumulative rare/magic CHECK share exceeds the cap."""
    from pricing.triage.engine import matches

    totals = Counter(item['category'] for item in corpus)
    checks = {i for i, verdict in enumerate(verdicts) if verdict == 'check'}
    accepted = []
    for pattern in patterns:
        if any(matches(item, pattern) and supported_rows(item, pattern) for item in negatives):
            continue
        added = {
            i
            for i, (item, verdict) in enumerate(zip(corpus, verdicts, strict=True))
            if verdict in ('vendor', 'self') and matches(item, pattern) and supported_rows(item, pattern)
        }
        proposed = checks | added
        if any(
            sum(corpus[i]['category'] == category for i in proposed) > totals[category] * limit
            for category in ('rare', 'magic')
        ):
            continue
        checks = proposed
        accepted.append(pattern)
    return accepted


def lookup(item, index):
    from pricing.triage.engine import matches
    from pricing.triage.rule_index import candidates

    for rule in candidates(item, index):
        if matches(item, rule) and (rows := supported_rows(item, rule)):
            return rule | {'reference_band': band_for(rule['category'], rule['family'], rows)}
    return None


def supported_rows(item, pattern):
    """Three seller minima must support whole vectors, not independent axis floors."""
    props = item.get('properties', {})
    rows = [
        row
        for row in pattern['supporters']
        if all(type(props.get(key)) in (int, float) and props[key] >= value for key, value in row['properties'].items())
    ]
    sellers = {}
    for row in rows:
        if row.get('seller_id'):
            seller = str(row['seller_id'])
            sellers[seller] = min(sellers.get(seller, math.inf), row['ask_ist'])
    return rows if sum(value >= pattern['keep_ist'] for value in sellers.values()) >= 3 else []


def guide_negatives(cases):
    """Explicit guide VENDOR examples constrain learned subsets, not market prices."""
    from pricing.triage.guide_cases import item_from_spec

    result = []
    for case in cases:
        if case.get('classification') == 'own-use':
            continue
        entries = case.get('examples')
        if entries is None:
            entries = [
                {'spec': spec, 'expected': case.get('expected')}
                for spec in case.get('specs', []) or ([case['spec']] if case.get('spec') else [])
            ] + [
                {'item': item, 'expected': case.get('expected')}
                for item in case.get('items', []) or ([case['item']] if case.get('item') else [])
            ]
        for entry in entries:
            if entry.get('expected') == ['vendor']:
                item = item_from_spec(entry['spec']) if entry.get('spec') else entry['item']
                if item['category'] in AFFIXED:
                    result.append(item)
    return result
