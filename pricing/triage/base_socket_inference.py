"""Listing-only socket omission inference from supported price distributions."""

import json
from collections import defaultdict
from statistics import quantiles

from pricing.triage.bands import eligible, latest_rows


def key(row):
    return json.dumps([row.get('base_code') or row.get('name'), row.get('ethereal'), row.get('rarity')])


def distribution(rows):
    sellers = {}
    for row in rows:
        price, seller = row.get('ask_ist'), row.get('seller_id')
        if seller and type(price) in (int, float) and price > 0:
            sellers[str(seller)] = min(price, sellers.get(str(seller), price))
    values = sorted(sellers.values())
    return {
        'sellers': len(values),
        'quartiles': quantiles(values, n=4, method='inclusive') if len(values) >= 3 else None,
    }


def compile_inferences(rows, utility):
    counts = defaultdict(set)
    for entry in utility:
        if entry.get('details', {}).get('legality') == 'verified_type_and_capacity':
            counts[entry['base_code']].add(entry['sockets'])
    groups = defaultdict(lambda: defaultdict(list))
    for row in latest_rows(rows):
        if (
            eligible(row)
            and row.get('category') == 'base'
            and row.get('amount') == 1
            and row.get('rarity') in ('normal', 'superior')
            and type(row.get('ethereal')) is bool
            and row.get('socket_contents') != 'filled'
            and '934' not in row.get('properties', {})
        ):
            groups[key(row)][row.get('sockets')].append(row)
    result = {}
    for identity, variants in sorted(groups.items()):
        if None not in variants:
            continue
        sample = variants[None][0]
        allowed = {0} | counts[sample.get('base_code')]
        evidence = {str(n): distribution(rs) for n, rs in variants.items() if n in allowed or n is None}
        unknown = evidence['None']['quartiles']
        supported = {int(n): d['quartiles'] for n, d in evidence.items() if n != 'None' and d['quartiles'] is not None}
        matches = [
            n
            for n, points in supported.items()
            if unknown is not None and all(max(a, b) / min(a, b) <= 1.5 for a, b in zip(unknown, points, strict=True))
        ]
        complete = unknown is not None and 0 in supported and any(n > 0 for n in supported)
        inferred = matches[0] if complete and len(matches) == 1 else None
        result[identity] = {
            'name': sample.get('name'),
            'inferred_sockets': inferred,
            'method': 'unique Q1/median/Q3 match within 1.5x; >=3 sellers for missing, zero and runeword sockets',
            'reason': 'matched'
            if inferred is not None
            else 'ambiguous'
            if complete and len(matches) > 1
            else 'unmatched'
            if complete
            else 'insufficient evidence',
            'distributions': evidence,
        }
    return result


def apply(row, table):
    if (
        row.get('category') != 'base'
        or row.get('amount') != 1
        or row.get('sockets') is not None
        or '402' in row.get('properties', {})
    ):
        return row
    evidence = table.get(key(row), {})
    count = evidence.get('inferred_sockets')
    if count is None or row.get('socket_contents') == 'filled' or '934' in row.get('properties', {}):
        return row
    return row | {
        'sockets': count,
        'facet_basis': row.get('facet_basis', {})
        | {
            'sockets': {'kind': 'price_distribution_inference', 'cohort': key(row), 'method': evidence['method']},
        },
    }
