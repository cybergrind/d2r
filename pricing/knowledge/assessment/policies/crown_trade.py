"""Two-socket Crown demand, independent of inserts and intrinsic premium pricing."""

import hashlib
import json
from datetime import date
from functools import lru_cache
from math import isfinite
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES, reviewed_native
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.market import scope_status


ROOT = Path(__file__).resolve().parents[4]
RULES = ROOT / 'pricing/knowledge/assessment/rules/crown_trade.json'
GUIDES = ROOT / 'pricing/data/wp-a-builds.json'
MARKET = ROOT / 'pricing/data/appraisal-market.jsonl'
NATIVE = tuple(ROOT / 'third-parties/d2data/json' / f'{name}.json' for name in NATIVE_HASHES)
IDENTITY = ('unique', 'Crown of Ages')
BOUNDS = {'31:0': (349, 399), '36:0': (10, 15), **{f'{s}:0': (20, 30) for s in (39, 41, 43, 45)}}


def inputs():
    return dict.fromkeys((RULES, GUIDES, MARKET, *NATIVE), 'reviewed two-socket Crown trade evidence')


@lru_cache(maxsize=2)
def validate(raw, guides, market, native):
    review = json.loads(raw)
    if review['id'] != 'crown-two-socket-shell' or review['scope'] != 'SC / Non-Ladder / PC / RotW':
        raise ValueError('Invalid Crown trade scope')
    date.fromisoformat(review['reviewed_at'])
    if hashlib.sha256(guides).hexdigest() != review['guide_sha256']:
        raise ValueError('Crown guide changed')
    source = json.loads(guides)
    expected = {
        '/meteor-sorceress/variants/4/player/Helmet/0': 'Crown of Ages (2 sockets: 2x Jewel 7% FHR / 15 All Res)',
        '/smite-paladin/variants/2/player/Helmet/0': (
            "Crown of Ages (Ber Rune + Protector's Stone Colossal Jewel per planner)"
        ),
    }
    if review['guide_entries'] != expected or any(resolve_pointer(source, p) != v for p, v in expected.items()):
        raise ValueError('Invalid Crown two-insert demand')
    if hashlib.sha256(market).hexdigest() != review['market_sha256']:
        raise ValueError('Crown market evidence changed')
    if not reviewed_native(ROOT, dict(zip(NATIVE, native, strict=True)).__getitem__):
        raise ValueError('Crown native mechanics changed')
    ids = review['evidence_ids']
    rows = [r for line in market.splitlines() if (r := json.loads(line))['id'] in ids]
    if not ids or len(set(ids)) != len(ids) or len(rows) != len(ids):
        raise ValueError('Missing or duplicate Crown evidence')
    sellers = set()
    for row in rows:
        props, ask = row.get('properties', {}), row.get('ask_ist')
        if (
            (row.get('rarity'), row.get('name')) != IDENTITY
            or row.get('base_code') != 'urn'
            or row.get('ethereal') is not False
            or props.get('738') not in (None, False)
            or row.get('scope_status') != 'verified'
            or scope_status(props) != 'verified'
            or row.get('evidence_kind') != 'ask'
            or row.get('unit_policy') != 'single_item'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or type(ask) not in (int, float)
            or not isfinite(ask)
            or ask <= 0
            or not row.get('seller_id')
            or type(row.get('sockets')) is not int
            or row['sockets'] != 2
            or any(
                type(props.get(k)) is not int or not lo <= props[k] <= hi
                for k, lo, hi in [('402', 2, 2), ('1855', 349, 399), ('441', 20, 30), ('1865', 10, 15)]
            )
            or ('413' in props and props['413'] != props['1865'])
        ):
            raise ValueError('Invalid Crown shell evidence')
        date.fromisoformat(row['observed_at'][:10])
        sellers.add(row['seller_id'])
    if len(sellers) < 3:
        raise ValueError('Insufficient independent Crown evidence')
    return review['reviewed_at']


def reviewed_date():
    return validate(
        read_artifact(RULES), read_artifact(GUIDES), read_artifact(MARKET), tuple(read_artifact(p) for p in NATIVE)
    )


def assess(facts):
    if (facts.rarity, facts.name) != IDENTITY:
        return {}
    pending = {'status': 'unresolved', 'reason': 'Crown socket count or native item facts need verification.'}
    definition, _ = resolve_named_definition(facts, identity_only=True)
    if (
        definition is None
        or facts.base_code != 'urn'
        or facts.identified is not True
        or facts.ethereal is not False
        or facts.capture_complete is not True
        or type(facts.sockets) is not int
        or facts.sockets not in (1, 2)
        or facts.socket_contents not in ('empty', 'filled', 'unknown', None)
    ):
        return pending
    values = {}
    for key, (low, high) in BOUNDS.items():
        row = facts.stats.get(key, {})
        value = row.get('value')
        if (
            row.get('status') != 'decoded'
            or type(value) is not int
            or value < low
            or (facts.socket_contents == 'empty' and value > high)
        ):
            return pending
        values[key] = value
    if facts.socket_contents == 'empty' and len({values[f'{s}:0'] for s in (39, 41, 43, 45)}) != 1:
        return pending
    if facts.sockets == 1:
        return {
            'status': 'unresolved',
            'reason': 'One socket cannot fit the reviewed two-insert setups; trade evidence is thin.',
        }
    try:
        reviewed = reviewed_date()
    except OSError, ValueError, KeyError, TypeError:
        return {**pending, 'reason': 'Crown trade evidence requires review.'}
    reason = 'Two sockets support defensive Uber setups; no proven intrinsic-roll premium.'
    if facts.socket_contents != 'empty':
        reason += ' Assess inserts separately.'
    return {
        'status': 'candidate',
        'assessment_scope': 'recoverable_shell',
        'reason': reason,
        'material_stats': [],
        'basis': 'reviewed_build_demand_and_shell_asks',
        'reviewed_at': reviewed,
    }
