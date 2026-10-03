"""Current scoped Dracul asking cohorts; missing variant evidence stays unresolved."""

import hashlib
import json
from datetime import date

from pricing.knowledge.assessment.maintenance.trade_war_traveler_evidence import asking_terms
from pricing.knowledge.assessment.policies.draculs_ethereal import infer
from pricing.knowledge.market import scope_status


IDENTITY = ('unique', "Dracul's Grasp")
MARKET = 'pricing/data/appraisal-market.jsonl'
GROUPS = ('perfect_leech', 'lower_leech', 'unproven')


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
        legal = all(
            type(props.get(k)) is int and low <= props[k] <= high
            for k, low, high in (('462', 7, 10), ('437', 10, 15), ('425', 90, 120), ('721', 5, 10))
        )
        group = (
            ('perfect_leech' if props['462'] == 10 else 'lower_leech') if legal and infer(row) is False else 'unproven'
        )
        groups[group]['rows'].append(row['id'])
        groups[group]['sellers'].add(row['seller_id'])
        if terms == 'barter_ask':
            groups[group]['barter_rows'].append(row['id'])
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
    return len(groups['perfect_leech']['sellers']) >= 3 and len(groups['lower_leech']['sellers']) < 3


def load_evidence(root, document, policies, scopes):
    if not any((r['quality'], r['name']) == IDENTITY and r['scope'] in scopes for r in document['rows']):
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    trade = policies.get(IDENTITY, {}).get('trade_qualification', {})
    if trade.get('market_snapshot') != snapshot:
        return {}
    evidence = audit(json.loads(line) for line in raw.splitlines())
    if len(trade.get('bands', [])) != 1:
        return {}
    for band, group in zip(trade['bands'], ('perfect_leech',), strict=True):
        if not set(band['evidence_ids']) <= set(evidence['cohorts'][group]['rows']):
            return {}
    return {IDENTITY: {**evidence, 'market_snapshot': snapshot}}
