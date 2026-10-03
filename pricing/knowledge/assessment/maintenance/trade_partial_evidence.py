"""Dated cache censuses for explicitly reviewed unknown jewelry roll regions.

A thin priced cohort is evidence-unavailable, never use-only or worthless.
The entire normalized market snapshot is pinned; new evidence invalidates review.
"""

import hashlib
import json
from datetime import date
from math import isfinite

from pricing.knowledge.assessment.maintenance.trade_compound_rolls import legal_vectors


MARKET = 'pricing/data/appraisal-market.jsonl'
REGIONS = {
    ('unique', "Mara's Kaleidoscope"): ('441', '39:0', 20, 26, {f'{s}:0': (20, 30) for s in (39, 41, 43, 45)}),
    ('unique', 'Nagelring'): ('461', '80:0', 15, 29, {'19:0': (50, 75), '80:0': (15, 30)}),
}


def audit_region(observations, identity):
    prop, key, minimum, maximum, _ = REGIONS[identity]
    sellers, priced, unpriced = set(), set(), set()
    for row in observations:
        properties = row.get('properties', {})
        value = properties.get(prop)
        if prop == '441' and value is None:
            members = [properties.get(k) for k in ('427', '428', '426', '401')]
            if all(type(v) is int for v in members) and len(set(members)) == 1:
                value = members[0]
        if (
            (row.get('rarity'), row.get('name')) != identity
            or row.get('scope_status') != 'verified'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or row.get('unit_policy') != 'single_item'
            or row.get('ethereal') is not False
            or type(row.get('sockets')) is not int
            or row['sockets'] != 0
            or row.get('socket_contents') != 'empty'
            or row.get('evidence_kind') != 'ask'
            or not isinstance(row.get('seller_id'), str)
            or not row['seller_id']
            or not isinstance(row.get('id'), str)
            or not row['id']
            or type(value) is not int
            or not minimum <= value <= maximum
        ):
            continue
        try:
            date.fromisoformat(row.get('observed_at'))
        except TypeError, ValueError:
            continue
        ask = row.get('ask_ist')
        if type(ask) in (int, float) and isfinite(ask) and ask > 0:
            sellers.add(row['seller_id'])
            priced.add(row['id'])
        else:
            unpriced.add(row['id'])
    return {
        'quality': identity[0],
        'name': identity[1],
        'property': prop,
        'key': key,
        'minimum': minimum,
        'maximum': maximum,
        'priced_sellers': sorted(sellers),
        'priced_rows': sorted(priced),
        'unpriced_rows': sorted(unpriced),
    }


def thin_region(evidence):
    identity = evidence.get('quality'), evidence.get('name')
    if identity not in REGIONS:
        return False
    prop, key, minimum, maximum, _ = REGIONS[identity]
    sellers = evidence.get('priced_sellers')
    return (
        (evidence.get('property'), evidence.get('key'), evidence.get('minimum'), evidence.get('maximum'))
        == (prop, key, minimum, maximum)
        and isinstance(sellers, list)
        and all(isinstance(s, str) and s for s in sellers)
        and len(sellers) == len(set(sellers)) < 3
    )


def reviewed_vectors(evidence, bounds, compounds):
    if not thin_region(evidence):
        return frozenset()
    identity = evidence['quality'], evidence['name']
    if bounds != REGIONS[identity][4]:
        return frozenset()
    keys = tuple(sorted(bounds))
    points = {k: range(low, high + 1) for k, (low, high) in bounds.items()}
    position = keys.index(evidence['key'])
    return frozenset(
        vector
        for vector in legal_vectors(keys, points, compounds)
        if evidence['minimum'] <= vector[position] <= evidence['maximum']
    )


def load_evidence(root, document, policies, scopes):
    identities = {(r['quality'], r['name']) for r in document['rows'] if r['scope'] in scopes}
    if not identities:
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    observations = [json.loads(line) for line in raw.splitlines()]
    return {
        identity: {**audit_region(observations, identity), 'market_snapshot': snapshot}
        for identity in identities
        if identity in REGIONS
        and policies.get(identity, {}).get('trade_qualification', {}).get('market_snapshot') == snapshot
    }
