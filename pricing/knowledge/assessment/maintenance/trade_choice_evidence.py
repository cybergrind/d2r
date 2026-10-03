"""Source-bound census of Opalvein's six mutually exclusive native choices.

Unreviewed choices remain unknown only while their independently priced cohorts
are thin. Missing evidence is never a use-only or worthless disposition.
"""

import hashlib
import json
from datetime import date
from math import isfinite

from pricing.knowledge.market import scope_status


MARKET = 'pricing/data/appraisal-market.jsonl'
IDENTITY = ('unique', 'Opalvein')
CHOICES = {
    'magic': ('1879', ('357:0',), 3, 5),
    'physical': ('510', ('17:0', '18:0'), 20, 40),
    'fire': ('750', ('329:0',), 3, 5),
    'cold': ('747', ('331:0',), 3, 5),
    'lightning': ('743', ('330:0',), 3, 5),
    'poison': ('783', ('332:0',), 3, 5),
}


def _bounded(value, low, high):
    return type(value) is int and low <= value <= high


def _resistance(properties):
    members = [properties.get(k) for k in ('427', '428', '426', '401')]
    aggregate = properties.get('441')
    if aggregate is None:
        return members[0] if all(type(v) is int for v in members) and len(set(members)) == 1 else None
    # A supplied component may corroborate the aggregate, never contradict it.
    if any(v is not None and (type(v) is not int or v != aggregate) for v in members):
        return None
    return aggregate


def audit_choices(observations):
    """Recompute from raw normalized rows, never from a saved review count."""
    cohorts = {name: {'sellers': set(), 'rows': set()} for name in CHOICES}
    properties = {spec[0]: name for name, spec in CHOICES.items()}
    for row in observations:
        props = row.get('properties', {})
        ask = row.get('ask_ist')
        if (
            (row.get('rarity'), row.get('name')) != IDENTITY
            or row.get('scope_status') != 'verified'
            or scope_status(props) != 'verified'
            or row.get('evidence_kind') != 'ask'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or row.get('unit_policy') != 'single_item'
            or row.get('ethereal') is not False
            or type(row.get('sockets')) is not int
            or row['sockets'] != 0
            or row.get('socket_contents') != 'empty'
            or not isinstance(row.get('seller_id'), str)
            or not row['seller_id']
            or not isinstance(row.get('id'), str)
            or not row['id']
            or type(ask) not in (int, float)
            or not isfinite(ask)
            or ask <= 0
        ):
            continue
        try:
            date.fromisoformat(row['observed_at'][:10])
        except KeyError, TypeError, ValueError:
            continue
        selected = set(props).intersection(properties)
        if len(selected) != 1:
            continue
        prop = selected.pop()
        name = properties[prop]
        _, _, low, high = CHOICES[name]
        if not (
            _bounded(props[prop], low, high)
            and _bounded(_resistance(props), 6, 8)
            and _bounded(props.get('721'), 1, 3)
            and _bounded(props.get('511'), 1, 3)
        ):
            continue
        cohorts[name]['sellers'].add(row['seller_id'])
        cohorts[name]['rows'].add(row['id'])
    return {
        'quality': IDENTITY[0],
        'name': IDENTITY[1],
        'choices': {
            name: {
                'property': prop,
                'keys': list(keys),
                'minimum': low,
                'maximum': high,
                'priced_rows': sorted(cohorts[name]['rows']),
                'priced_sellers': sorted(cohorts[name]['sellers']),
            }
            for name, (prop, keys, low, high) in CHOICES.items()
        },
    }


def reviewed_choices(evidence, supported):
    if (evidence.get('quality'), evidence.get('name')) != IDENTITY or set(evidence.get('choices', {})) != set(CHOICES):
        return False
    if set(supported) != {'329:0', '331:0'} or len(supported) != 2:
        return False
    for name, (prop, keys, low, high) in CHOICES.items():
        row = evidence['choices'][name]
        if (row.get('property'), row.get('keys'), row.get('minimum'), row.get('maximum')) != (
            prop,
            list(keys),
            low,
            high,
        ):
            return False
        sellers, rows = row.get('priced_sellers'), row.get('priced_rows')
        if any(
            not isinstance(v, list) or any(not isinstance(s, str) or not s for s in v) or len(v) != len(set(v))
            for v in (sellers, rows)
        ):
            return False
        if len(sellers) > len(rows) or (len(sellers) >= 3) != (name in ('fire', 'cold')):
            return False
    return True


def load_evidence(root, document, policies, scopes):
    if not any((r['quality'], r['name']) == IDENTITY and r['scope'] in scopes for r in document['rows']):
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    if policies.get(IDENTITY, {}).get('trade_qualification', {}).get('market_snapshot') != snapshot:
        return {}
    return {IDENTITY: {**audit_choices(json.loads(line) for line in raw.splitlines()), 'market_snapshot': snapshot}}
