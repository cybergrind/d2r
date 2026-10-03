"""Scoped asking census for original/upgraded War Traveler roll reviews."""

import hashlib
import json
from datetime import date
from math import isfinite

from pricing.knowledge.assessment.policies.trade_barter import validate_barter
from pricing.knowledge.assessment.policies.war_traveler_ethereal import infer
from pricing.knowledge.market import scope_status


IDENTITY = ('unique', 'War Traveler')
MARKET = 'pricing/data/appraisal-market.jsonl'
GROUPS = ('perfect', 'lower', 'unproven')


def asking_terms(row):
    ask = row.get('ask_ist')
    if type(ask) in (int, float) and isfinite(ask) and ask > 0:
        return 'converted_ask'
    if ask is not None:
        return None
    try:
        validate_barter(
            {
                'market_evidence': [row],
                'barter_evidence_ids': [row['id']],
                'default_status': 'candidate',
                'default_evidence_ids': [row['id']],
                'bands': [],
            }
        )
    except KeyError, TypeError, ValueError:
        return None
    return 'barter_ask'


def audit(observations):
    groups = {key: {'rows': [], 'sellers': set(), 'barter_rows': []} for key in GROUPS}
    for row in observations:
        if (
            (row.get('rarity'), row.get('name')) != IDENTITY
            or row.get('scope_status') != 'verified'
            or scope_status(row.get('properties', {})) != 'verified'
            or row.get('evidence_kind') != 'ask'
            or row.get('unit_policy') != 'single_item'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or not isinstance(row.get('id'), str)
            or not row['id']
            or not isinstance(row.get('seller_id'), str)
            or not row['seller_id']
            or not (terms := asking_terms(row))
        ):
            continue
        try:
            date.fromisoformat(row['observed_at'][:10])
        except KeyError, ValueError, TypeError:
            continue
        props = row.get('properties', {})
        native = all(
            type(props.get(k)) is int and lo <= props[k] <= hi
            for k, lo, hi in [('461', 30, 50), ('425', 150, 190), ('415', 5, 10)]
        )
        key = ('perfect' if props['461'] == 50 else 'lower') if native and infer(row) is False else 'unproven'
        groups[key]['rows'].append(row['id'])
        groups[key]['sellers'].add(row['seller_id'])
        if terms == 'barter_ask':
            groups[key]['barter_rows'].append(row['id'])
    return {
        'identity': list(IDENTITY),
        'cohorts': {k: {field: sorted(values) for field, values in v.items()} for k, v in groups.items()},
    }


def reviewed(evidence):
    if evidence.get('identity') != list(IDENTITY) or set(evidence.get('cohorts', {})) != set(GROUPS):
        return False
    groups = evidence['cohorts']
    for row in groups.values():
        if any(
            not isinstance(row.get(k), list)
            or len(row[k]) != len(set(row[k]))
            or any(not isinstance(s, str) or not s for s in row[k])
            for k in ('rows', 'sellers', 'barter_rows')
        ):
            return False
        if len(row['sellers']) > len(row['rows']) or set(row['barter_rows']) - set(row['rows']):
            return False
    return len(groups['perfect']['sellers']) >= 3 and len(groups['lower']['sellers']) < 3


def load_evidence(root, document, policies, scopes):
    if not any((r['quality'], r['name']) == IDENTITY and r['scope'] in scopes for r in document['rows']):
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    trade = policies.get(IDENTITY, {}).get('trade_qualification', {})
    if trade.get('market_snapshot') != snapshot:
        return {}
    evidence = audit(json.loads(line) for line in raw.splitlines())
    if set(trade['bands'][0]['evidence_ids']) != set(evidence['cohorts']['perfect']['rows']):
        return {}
    return {IDENTITY: {**evidence, 'market_snapshot': snapshot}}
