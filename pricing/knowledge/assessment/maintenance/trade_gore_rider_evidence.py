"""Current scoped asking cohorts for original and upgraded Gore Rider rules."""

import hashlib
import json
from datetime import date

from pricing.knowledge.assessment.maintenance.trade_war_traveler_evidence import asking_terms
from pricing.knowledge.assessment.policies.gore_rider_defense import variant_code
from pricing.knowledge.market import scope_status


IDENTITY = ('unique', 'Gore Rider')
MARKET = 'pricing/data/appraisal-market.jsonl'
GROUPS = ('original', 'upgraded_perfect', 'upgraded_lower', 'unproven')


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
        code = variant_code(row)
        group = (
            (
                'original'
                if code == 'xhb'
                else 'upgraded_perfect'
                if row['properties']['425'] == 200
                else 'upgraded_lower'
            )
            if code
            else 'unproven'
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
    return (
        len(groups['original']['sellers']) >= 3
        and len(groups['upgraded_perfect']['sellers']) >= 3
        and len(groups['upgraded_lower']['sellers']) < 3
    )


def load_evidence(root, document, policies, scopes):
    if not any((r['quality'], r['name']) == IDENTITY and r['scope'] in scopes for r in document['rows']):
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    trade = policies.get(IDENTITY, {}).get('trade_qualification', {})
    if trade.get('market_snapshot') != snapshot:
        return {}
    evidence = audit(json.loads(line) for line in raw.splitlines())
    if len(trade.get('bands', [])) != 2:
        return {}
    for band, group in zip(trade['bands'], ('original', 'upgraded_perfect'), strict=True):
        if not set(band['evidence_ids']) <= set(evidence['cohorts'][group]['rows']):
            return {}
    return {IDENTITY: {**evidence, 'market_snapshot': snapshot}}
