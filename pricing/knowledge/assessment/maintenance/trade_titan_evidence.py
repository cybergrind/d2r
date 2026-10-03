"""Independent original/upgraded Titan cohorts, including reviewed unknown regions."""

import hashlib
import json
from datetime import date
from math import isfinite

from pricing.knowledge.assessment.maintenance.trade_titan import BASE_CODES, IDENTITY, THRESHOLDS
from pricing.knowledge.market import scope_status


MARKET = 'pricing/data/appraisal-market.jsonl'
COHORTS = {
    f'{code}/{label}': (code, ethereal, low, high)
    for code, threshold in THRESHOLDS.items()
    for label, ethereal, low, high in (
        ('premium', True, threshold, 200),
        ('lower', True, 150, threshold - 1),
        ('nonethereal', False, 150, 200),
        ('unknown_ethereal', None, 150, 200),
    )
}


def audit_titan(observations):
    cohorts = {key: {'rows': set(), 'sellers': set()} for key in (*COHORTS, 'unknown_base')}
    for row in observations:
        p, ask = row.get('properties', {}), row.get('ask_ist')
        if (
            (row.get('rarity'), row.get('name')) != IDENTITY
            or row.get('scope_status') != 'verified'
            or scope_status(p) != 'verified'
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
            or type(p.get('510')) is not int
            or not 150 <= p['510'] <= 200
            or type(p.get('462')) is not int
            or not 5 <= p['462'] <= 9
        ):
            continue
        try:
            date.fromisoformat(row['observed_at'][:10])
        except KeyError, TypeError, ValueError:
            continue
        base, ethereal = row.get('base_code'), row.get('ethereal')
        if base is None:
            key = 'unknown_base'
        else:
            key = next(
                (
                    key
                    for key, (code, eth, low, high) in COHORTS.items()
                    if base == code and ethereal is eth and low <= p['510'] <= high
                ),
                None,
            )
        if key is None:
            continue
        cohorts[key]['rows'].add(row['id'])
        cohorts[key]['sellers'].add(row['seller_id'])
    return {
        'quality': IDENTITY[0],
        'name': IDENTITY[1],
        'base_codes': dict(BASE_CODES),
        'leech_range': [5, 9],
        'cohorts': {
            key: {
                'variant': list(COHORTS[key]) if key in COHORTS else None,
                'priced_rows': sorted(v['rows']),
                'priced_sellers': sorted(v['sellers']),
            }
            for key, v in cohorts.items()
        },
    }


def reviewed_variants(evidence):
    if (
        (evidence.get('quality'), evidence.get('name')) != IDENTITY
        or evidence.get('base_codes') != BASE_CODES
        or evidence.get('leech_range') != [5, 9]
        or set(evidence.get('cohorts', {})) != {*COHORTS, 'unknown_base'}
    ):
        return False
    for key, row in evidence['cohorts'].items():
        expected = list(COHORTS[key]) if key in COHORTS else None
        if row.get('variant') != expected:
            return False
        sellers, rows = row.get('priced_sellers'), row.get('priced_rows')
        if any(
            not isinstance(v, list) or any(not isinstance(s, str) or not s for s in v) or len(v) != len(set(v))
            for v in (sellers, rows)
        ):
            return False
        if len(sellers) > len(rows):
            return False
        if key.endswith('/premium') and len(sellers) < 3:
            return False
        if key.endswith(('/lower', '/nonethereal')) and len(sellers) >= 3:
            return False
    return True


def load_evidence(root, document, policies, scopes):
    if not any((r['quality'], r['name']) == IDENTITY and r['scope'] in scopes for r in document['rows']):
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    if policies.get(IDENTITY, {}).get('trade_qualification', {}).get('market_snapshot') != snapshot:
        return {}
    return {IDENTITY: {**audit_titan(json.loads(line) for line in raw.splitlines()), 'market_snapshot': snapshot}}
