"""Underlying Stormshield asking interest, separate from defense and insert value."""

import hashlib
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.market import scope_status


ROOT = Path(__file__).resolve().parents[4]
RULES = ROOT / 'pricing/knowledge/assessment/rules/stormshield_trade.json'
GUIDES = ROOT / 'pricing/data/wp-a-builds.json'
MARKET = ROOT / 'pricing/data/appraisal-market.jsonl'
NATIVE = tuple(ROOT / 'third-parties/d2data/json' / f'{name}.json' for name in NATIVE_HASHES)
REASON = 'Fixed damage reduction and blocking support Uber setups; ordinary defense still qualifies.'


def inputs():
    return dict.fromkeys((RULES, GUIDES, MARKET, *NATIVE), 'reviewed Stormshield underlying-item demand')


@lru_cache(maxsize=2)
def validate(raw, guides, market, native):
    review = json.loads(raw)
    if review['scope'] != 'SC / Non-Ladder / PC / RotW' or review['id'] != 'stormshield-underlying':
        raise ValueError('Invalid Stormshield trade scope')
    date.fromisoformat(review['reviewed_at'])
    if (
        hashlib.sha256(guides).hexdigest() != review['guide_sha256']
        or hashlib.sha256(market).hexdigest() != review['market_sha256']
    ):
        raise ValueError('Stormshield source evidence changed')
    guide = json.loads(guides)
    if len(review['guide_variants']) < 2:
        raise ValueError('Missing Stormshield scoped build demand')
    for pointer, expected in review['guide_variants'].items():
        variant = resolve_pointer(guide, pointer)
        if (
            variant != expected
            or variant.get('name') != 'Ubers'
            or 'Stormshield' not in json.dumps(variant.get('player', {}))
        ):
            raise ValueError('Stormshield demand must be the reviewed Uber variants, not Hardcore uses')
    for name, data in zip(NATIVE_HASHES, native, strict=True):
        if hashlib.sha256(data).hexdigest() != NATIVE_HASHES[name]:
            raise ValueError('Stormshield native definitions changed')
    ids = review['evidence_ids']
    rows = [r for line in market.splitlines() if (r := json.loads(line))['id'] in ids]
    if not ids or len(set(ids)) != len(ids) or len(rows) != len(ids):
        raise ValueError('Missing or duplicate Stormshield asking evidence')
    sellers = set()
    for row in rows:
        props = row.get('properties', {})
        ask = row.get('ask_ist')
        sockets = row.get('sockets')
        if (
            (row.get('rarity'), row.get('name'), row.get('base_code')) != ('unique', 'Stormshield', 'uit')
            or row.get('ethereal') is not False
            or row.get('base_upgrade') not in (None, False)
            or row.get('scope_status') != 'verified'
            or scope_status(props) != 'verified'
            or row.get('evidence_kind') != 'ask'
            or row.get('listing_status') != {'active': True, 'selling': True, 'completed': False}
            or row.get('unit_policy') != 'single_item'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or type(ask) not in (int, float)
            or not math.isfinite(ask)
            or ask <= 0
            or not isinstance(row.get('seller_id'), str)
            or not row['seller_id']
            or (sockets is not None and (type(sockets) is not int or sockets not in (0, 1)))
            or ('402' in props and (type(props['402']) is not int or props['402'] not in (0, 1)))
            or (sockets is not None and '402' in props and sockets != props['402'])
            or (row.get('socket_contents') == 'filled' and (sockets == 0 or props.get('402') == 0))
            or type(props.get('1855')) is not int
            or not 133 <= props['1855'] <= 142
            or any(p in props for p in ('436', '399', '425', '934'))
            or ('738' in props and props['738'] is not False)
            or props.get('930') not in (None, 'Elite')
            or ('1216' in props and props['1216'] is not False)
        ):
            raise ValueError('Invalid Stormshield underlying-item observation')
        date.fromisoformat(row['observed_at'][:10])
        sellers.add(row['seller_id'])
    if len(sellers) < 3:
        raise ValueError('Insufficient independent Stormshield sellers')
    return review['reviewed_at']


def reviewed_date():
    return validate(
        read_artifact(RULES), read_artifact(GUIDES), read_artifact(MARKET), tuple(read_artifact(p) for p in NATIVE)
    )


def assess(facts):
    if (facts.rarity, facts.name) != ('unique', 'Stormshield'):
        return {}
    pending = {'status': 'unresolved', 'reason': 'Stormshield native benefits or variant need verification.'}
    definition, _ = resolve_named_definition(facts, identity_only=True)
    defense = facts.stats.get('31:0', {})
    level = facts.stats.get('214:0', {})
    fixed = {'36:0': 35, '102:0': 35, '0:0': 30, '41:0': 25, '43:0': 60}
    if (
        definition is None
        or facts.base_code != 'uit'
        or facts.identified is not True
        or facts.ethereal is not False
        or facts.capture_complete is not True
        or type(facts.sockets) is not int
        or facts.sockets not in (0, 1)
        or facts.socket_contents not in ('empty', 'filled', 'unknown', None)
        or (facts.socket_contents == 'filled' and facts.sockets == 0)
        or defense.get('status') != 'decoded'
        or type(defense.get('value')) is not int
        or defense['value'] < 133
        or ((facts.sockets == 0 or facts.socket_contents == 'empty') and defense['value'] > 148)
        or level.get('status') != 'decoded'
        or type(level.get('raw')) is not int
        or level['raw'] != 30
        or any(
            facts.stats.get(k, {}).get('status') != 'decoded'
            or type(facts.stats[k].get('value')) is not int
            or facts.stats[k]['value'] < minimum
            for k, minimum in fixed.items()
        )
    ):
        return pending
    try:
        reviewed = reviewed_date()
    except OSError, ValueError, KeyError, TypeError:
        return {**pending, 'reason': 'Stormshield trade evidence requires review.'}
    return {
        'status': 'candidate',
        'assessment_scope': 'underlying_item',
        'reason': REASON
        + (' Assess inserts separately.' if facts.sockets and facts.socket_contents != 'empty' else ''),
        'material_stats': [],
        'basis': 'reviewed_build_demand_and_underlying_item_asks',
        'reviewed_at': reviewed,
    }
