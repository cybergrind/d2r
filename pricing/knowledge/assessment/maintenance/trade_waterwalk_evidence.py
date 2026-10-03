"""Dated Waterwalk asking census; incomplete observations remain explicit leads."""

import hashlib
import json
from datetime import date
from pathlib import Path

from pricing.knowledge.assessment.maintenance.trade_war_traveler_evidence import asking_terms
from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES, reviewed_native
from pricing.knowledge.assessment.mechanics.waterwalk_defense import variant_code
from pricing.knowledge.market import scope_status


IDENTITY = ('unique', 'Waterwalk')
MARKET = 'pricing/data/appraisal-market.jsonl'
ROOT = Path(__file__).resolve().parents[4]


def exclusion(row):
    if row.get('scope_status') != 'verified' or scope_status(row.get('properties', {})) != 'verified':
        return 'unverified_scope'
    try:
        date.fromisoformat(row['observed_at'][:10])
    except KeyError, ValueError, TypeError:
        return 'undated'
    state = row.get('listing_status', {})
    if (
        row.get('evidence_kind') != 'ask'
        or state.get('active') is not True
        or state.get('selling') is not True
        or state.get('completed') is not False
    ):
        return 'not_active_selling_ask'
    if row.get('unit_policy') != 'single_item' or type(row.get('amount')) is not int or row['amount'] != 1:
        return 'ambiguous_unit'
    if not isinstance(row.get('seller_id'), str) or not row['seller_id']:
        return 'missing_seller'
    if not asking_terms(row):
        return 'invalid_asking_terms'
    return None


def audit(observations):
    unique = {}
    for row in observations:
        if (row.get('rarity'), row.get('name')) != IDENTITY:
            continue
        if not isinstance(row.get('id'), str) or not row['id']:
            raise ValueError('Waterwalk observation requires an ID')
        previous = unique.setdefault(row['id'], row)
        if previous != row:
            raise ValueError('Conflicting Waterwalk observation')
    excluded, groups, unproven = {}, {}, []
    supported = {'rows': [], 'sellers': set()}
    original = {'rows': [], 'sellers': set()}
    for row in unique.values():
        reason = exclusion(row)
        if reason:
            excluded.setdefault(reason, []).append(row['id'])
            continue
        props = row.get('properties', {})
        code = variant_code(row)
        life = props.get('418')
        if not code or type(life) is not int or not 45 <= life <= 65:
            unproven.append(row['id'])
            continue
        key = (code, life, props['425'], props['1855'])
        group = (
            original
            if code == 'xvb'
            else supported
            if key == ('uvb', 65, 210, 198)
            else groups.setdefault(key, {'rows': [], 'sellers': set()})
        )
        group['rows'].append(row['id'])
        group['sellers'].add(row['seller_id'])
    return {
        'identity': list(IDENTITY),
        'observations': len(unique),
        'supported': {k: sorted(v) for k, v in supported.items()},
        'original': {k: sorted(v) for k, v in original.items()},
        'unresolved_cohorts': [
            {
                'base_code': k[0],
                'life': k[1],
                'enhanced_defense': k[2],
                'defense': k[3],
                **{field: sorted(values) for field, values in group.items()},
            }
            for k, group in sorted(groups.items())
        ],
        'unproven': sorted(unproven),
        'excluded': {k: sorted(v) for k, v in sorted(excluded.items())},
    }


def reviewed(evidence):
    if evidence.get('identity') != list(IDENTITY) or type(evidence.get('observations')) is not int:
        return False
    seen = set()

    def ids(values):
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
            return False
        if len(set(values)) != len(values) or seen.intersection(values):
            return False
        seen.update(values)
        return True

    def cohort(group, minimum, maximum=None):
        if not isinstance(group, dict) or not ids(group.get('rows')):
            return False
        sellers = group.get('sellers')
        return (
            isinstance(sellers, list)
            and all(isinstance(v, str) and v for v in sellers)
            and len(sellers) == len(set(sellers))
            and minimum <= len(sellers) <= len(group['rows'])
            and (maximum is None or len(sellers) <= maximum)
        )

    if not cohort(evidence.get('original'), 3) or not cohort(evidence.get('supported'), 3):
        return False
    groups = evidence.get('unresolved_cohorts')
    if not isinstance(groups, list):
        return False
    keys = set()
    for group in groups:
        if not cohort(group, 1, 2):
            return False
        key = tuple(group.get(k) for k in ('base_code', 'life', 'enhanced_defense', 'defense'))
        if (
            key[0] != 'uvb'
            or any(type(v) is not int for v in key[1:])
            or not 45 <= key[1] <= 65
            or not 180 <= key[2] <= 210
            or key[3] not in {b * (100 + key[2]) // 100 for b in range(56, 66)}
            or key == ('uvb', 65, 210, 198)
            or key in keys
        ):
            return False
        keys.add(key)
    if not ids(evidence.get('unproven')):
        return False
    excluded = evidence.get('excluded')
    reasons = {
        'unverified_scope',
        'undated',
        'not_active_selling_ask',
        'ambiguous_unit',
        'missing_seller',
        'invalid_asking_terms',
    }
    if not isinstance(excluded, dict) or set(excluded) - reasons or not all(ids(v) for v in excluded.values()):
        return False
    return len(seen) == evidence['observations']


def load_evidence(root, document, policies, scopes):
    if not any((r['quality'], r['name']) == IDENTITY and r['scope'] in scopes for r in document['rows']):
        return {}
    raw = (root / MARKET).read_bytes()
    snapshot = {'path': MARKET, 'sha256': hashlib.sha256(raw).hexdigest()}
    trade = policies.get(IDENTITY, {}).get('trade_qualification', {})
    if trade.get('market_snapshot') != snapshot or len(trade.get('bands', [])) != 2:
        return {}
    evidence = audit(json.loads(line) for line in raw.splitlines())
    for band, group in zip(trade['bands'], ('original', 'supported'), strict=True):
        if not set(band['evidence_ids']) <= set(evidence[group]['rows']):
            return {}
    return {IDENTITY: {**evidence, 'market_snapshot': snapshot}}


def main():
    if not reviewed_native(ROOT):
        raise ValueError('Waterwalk native tables changed; review variant mechanics')
    rows = [json.loads(line) for line in (ROOT / MARKET).read_text().splitlines()]
    paths = [
        MARKET,
        str(Path(__file__).relative_to(ROOT)),
        'pricing/knowledge/assessment/mechanics/waterwalk_defense.py',
        'pricing/knowledge/assessment/maintenance/trade_war_traveler_evidence.py',
        *[f'third-parties/d2data/json/{name}.json' for name in NATIVE_HASHES],
    ]
    paths.extend(sorted({r['source'] for r in rows if (r.get('rarity'), r.get('name')) == IDENTITY}))
    paths.append('pricing/data/wp-f-ladder.json')
    evidence = audit(rows)
    result = {
        'schema_version': 1,
        'reviewed_at': date.today().isoformat(),
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        **evidence,
        'limitation': 'Census of asking evidence, not whole-item trade closure or numerical pricing.',
    }
    (ROOT / 'pricing/data/appraisal-waterwalk-evidence-census.json').write_text(json.dumps(result, indent=2) + '\n')
    print(
        json.dumps(
            {
                'observations': evidence['observations'],
                'supported_sellers': len(evidence['supported']['sellers']),
                'original_sellers': len(evidence['original']['sellers']),
                'unresolved_cohorts': len(evidence['unresolved_cohorts']),
                'unproven': len(evidence['unproven']),
                'excluded': {k: len(v) for k, v in evidence['excluded'].items()},
            }
        )
    )


if __name__ == '__main__':
    main()
