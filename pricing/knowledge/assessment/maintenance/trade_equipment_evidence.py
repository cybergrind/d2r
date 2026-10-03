"""Exact native equipment variants retain separate independent-seller censuses."""

import hashlib
import json
from datetime import date
from math import isfinite

from pricing.knowledge.market import scope_status


MARKET = 'pricing/data/appraisal-market.jsonl'
IDENTITY = ('unique', 'Sandstorm Trek')
# Verified Scarabshell Boots code in the native armor definition, not a name guess.
BASE = 'uvb'
RANGES = {'437': (10, 15), '582': (10, 15), '425': (140, 170), '401': (40, 70)}
GROUPS = ('ethereal_attributes', 'ethereal_ordinary', 'nonethereal', 'unknown_ethereal')


def audit_trek(observations):
    cohorts = {key: {'rows': set(), 'sellers': set()} for key in GROUPS}
    for row in observations:
        p, ask = row.get('properties', {}), row.get('ask_ist')
        if (
            (row.get('rarity'), row.get('name')) != IDENTITY
            or row.get('scope_status') != 'verified'
            or scope_status(p) != 'verified'
            or row.get('base_code') != BASE
            or row.get('evidence_kind') != 'ask'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or row.get('unit_policy') != 'single_item'
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
            or any(type(p.get(k)) is not int or not lo <= p[k] <= hi for k, (lo, hi) in RANGES.items())
        ):
            continue
        try:
            date.fromisoformat(row['observed_at'][:10])
        except KeyError, TypeError, ValueError:
            continue
        ethereal = row.get('ethereal')
        if ethereal is True:
            key = 'ethereal_attributes' if p['437'] == p['582'] == 15 else 'ethereal_ordinary'
        elif ethereal is False:
            key = 'nonethereal'
        elif ethereal is None:
            key = 'unknown_ethereal'
        else:
            continue
        cohorts[key]['rows'].add(row['id'])
        cohorts[key]['sellers'].add(row['seller_id'])
    return {
        'quality': IDENTITY[0],
        'name': IDENTITY[1],
        'base_code': BASE,
        'ranges': {k: list(v) for k, v in RANGES.items()},
        'cohorts': {
            k: {'priced_rows': sorted(v['rows']), 'priced_sellers': sorted(v['sellers'])} for k, v in cohorts.items()
        },
    }


def reviewed_variants(evidence):
    if (
        (evidence.get('quality'), evidence.get('name'), evidence.get('base_code')) != (*IDENTITY, BASE)
        or evidence.get('ranges') != {k: list(v) for k, v in RANGES.items()}
        or set(evidence.get('cohorts', {})) != set(GROUPS)
    ):
        return False
    for key, cohort in evidence['cohorts'].items():
        sellers, rows = cohort.get('priced_sellers'), cohort.get('priced_rows')
        if any(
            not isinstance(v, list) or any(not isinstance(x, str) or not x for x in v) or len(v) != len(set(v))
            for v in (sellers, rows)
        ):
            return False
        if len(sellers) > len(rows):
            return False
        if key == 'nonethereal' and len(sellers) >= 3:
            return False
        if key.startswith('ethereal_') and len(sellers) < 3:
            return False
    return True


def load_evidence(root, document, policies, scopes):
    if not any((r['quality'], r['name']) == IDENTITY and r['scope'] in scopes for r in document['rows']):
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    if policies.get(IDENTITY, {}).get('trade_qualification', {}).get('market_snapshot') != snapshot:
        return {}
    return {IDENTITY: {**audit_trek(json.loads(line) for line in raw.splitlines()), 'market_snapshot': snapshot}}
