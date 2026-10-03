"""Source-bound Arachnid census: supported perfect rolls and thin lower evidence."""

import hashlib
import json
from datetime import date
from math import isfinite

from pricing.knowledge.assessment.policies.market_ethereal_inference import BASE_CODE, IDENTITY, MODE, arachnid_ethereal
from pricing.knowledge.market import scope_status


MARKET = 'pricing/data/appraisal-market.jsonl'
GROUPS = ('perfect', 'lower', 'unproven')


def audit_arachnid(observations, *, definition=None):
    cohorts = {key: {'rows': set(), 'sellers': set()} for key in GROUPS}
    for row in observations:
        props, ask = row.get('properties', {}), row.get('ask_ist')
        if (
            (row.get('rarity'), row.get('name')) != IDENTITY
            or row.get('base_code') != BASE_CODE
            or row.get('scope_status') != 'verified'
            or scope_status(props) != 'verified'
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
            or type(props.get('425')) is not int
            or not 90 <= props['425'] <= 120
        ):
            continue
        try:
            date.fromisoformat(row['observed_at'][:10])
        except KeyError, TypeError, ValueError:
            continue
        key = (
            ('perfect' if props['425'] == 120 else 'lower')
            if arachnid_ethereal(row, definition=definition) is False
            else 'unproven'
        )
        cohorts[key]['rows'].add(row['id'])
        cohorts[key]['sellers'].add(row['seller_id'])
    return {
        'quality': IDENTITY[0],
        'name': IDENTITY[1],
        'base_code': BASE_CODE,
        'ed_range': [90, 120],
        'ethereal_inference': MODE,
        'cohorts': {
            k: {'priced_rows': sorted(v['rows']), 'priced_sellers': sorted(v['sellers'])} for k, v in cohorts.items()
        },
    }


def reviewed_variants(evidence):
    if (
        (evidence.get('quality'), evidence.get('name'), evidence.get('base_code')) != (*IDENTITY, BASE_CODE)
        or evidence.get('ed_range') != [90, 120]
        or evidence.get('ethereal_inference') != MODE
        or set(evidence.get('cohorts', {})) != set(GROUPS)
    ):
        return False
    for key, row in evidence['cohorts'].items():
        sellers, ids = row.get('priced_sellers'), row.get('priced_rows')
        if any(
            not isinstance(v, list) or any(not isinstance(s, str) or not s for s in v) or len(v) != len(set(v))
            for v in (sellers, ids)
        ):
            return False
        if len(sellers) > len(ids):
            return False
        if key == 'perfect' and len(sellers) < 3:
            return False
        if key == 'lower' and len(sellers) >= 3:
            return False
    return True


def load_evidence(root, document, policies, scopes, definitions):
    if not any((r['quality'], r['name']) == IDENTITY and r['scope'] in scopes for r in document['rows']):
        return {}
    variants = definitions.get(IDENTITY, ())
    if len(variants) != 1:
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    if policies.get(IDENTITY, {}).get('trade_qualification', {}).get('market_snapshot') != snapshot:
        return {}
    evidence = audit_arachnid((json.loads(line) for line in raw.splitlines()), definition=variants[0])
    return {IDENTITY: {**evidence, 'market_snapshot': snapshot}}
