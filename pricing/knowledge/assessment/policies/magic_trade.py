"""Reviewed magic-item trade demand, separate from numerical payload valuation."""

import hashlib
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.mechanics.jmod_shell import NATIVE_HASHES, shell_evidence
from pricing.knowledge.assessment.mechanics.shield_blocking import modifier_blocking
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.market import scope_status


ROOT = Path(__file__).resolve().parents[4]
RULES = ROOT / 'pricing/knowledge/assessment/rules/magic_trade.json'
GUIDES = ROOT / 'pricing/data/wp-a-blues.json'
MARKET = ROOT / 'pricing/data/appraisal-market.jsonl'
NATIVE = tuple(ROOT / 'third-parties/d2data/json' / f'{name}.json' for name in NATIVE_HASHES)


def inputs():
    return dict.fromkeys((RULES, GUIDES, MARKET, *NATIVE), 'reviewed magic-item trade evidence')


@lru_cache(maxsize=2)
def validate(raw, guides, market, native):
    review = json.loads(raw)
    if review['scope'] != 'SC / Non-Ladder / PC / RotW' or review['id'] != 'jmod-shell':
        raise ValueError('Invalid magic trade scope')
    date.fromisoformat(review['reviewed_at'])
    if hashlib.sha256(guides).hexdigest() != review['guide_sha256']:
        raise ValueError('Magic trade guide evidence changed')
    demand = resolve_pointer(json.loads(guides), "/Jeweler's Monarch of Deflecting")
    if demand['affixes_named'] != ["Jeweler's", 'of Deflecting'] or not demand['builds'] or not demand['notes']:
        raise ValueError('Missing JMOD guide demand')
    if hashlib.sha256(market).hexdigest() != review['market_sha256']:
        raise ValueError('Magic trade market evidence changed')
    selected = {r['id']: r for line in market.splitlines() if (r := json.loads(line))['id'] in review['evidence_ids']}
    if len(selected) != len(review['evidence_ids']):
        raise ValueError('Missing or duplicate JMOD evidence')
    native_bytes = dict(zip(NATIVE, native, strict=True))
    sellers = set()
    for row in selected.values():
        if (
            row.get('scope_status') != 'verified'
            or scope_status(row.get('properties', {})) != 'verified'
            or row.get('evidence_kind') != 'ask'
            or row.get('unit_policy') != 'single_item'
            or type(row.get('amount')) is not int
            or row['amount'] != 1
            or type(row.get('ask_ist')) not in (int, float)
            or not 0 < row['ask_ist'] < float('inf')
            or not row.get('seller_id')
            or shell_evidence(row, ROOT, native_bytes.__getitem__) is None
        ):
            raise ValueError('Invalid JMOD shell evidence')
        date.fromisoformat(row['observed_at'][:10])
        sellers.add(row['seller_id'])
    if len(sellers) < 3:
        raise ValueError('Insufficient independent JMOD evidence')
    return review['reviewed_at']


def reviewed_date():
    return validate(
        read_artifact(RULES),
        read_artifact(GUIDES),
        read_artifact(MARKET),
        tuple(read_artifact(path) for path in NATIVE),
    )


def assess(facts):
    if facts.rarity != 'magic' or facts.base_code != 'uit':
        return {}
    properties, gaps = dict(facts.properties), []
    modifier_blocking(facts, properties, gaps)
    if (
        facts.identified is not True
        or facts.ethereal is not False
        or facts.capture_complete is not True
        or type(facts.sockets) is not int
        or facts.sockets != 4
        or gaps
        or properties.get('446') != 20
        or any(
            facts.stats.get(key, {}).get('status') != 'decoded'
            or type(facts.stats.get(key, {}).get('value')) is not int
            or facts.stats[key]['value'] != value
            for key, value in {'102:0': 30}.items()
        )
    ):
        return {}
    try:
        reviewed = reviewed_date()
    except OSError, ValueError, KeyError, TypeError:
        return {}
    reason = 'JMOD base for endgame facet shields.'
    if facts.socket_contents == 'filled':
        reason += ' The shield remains useful after clearing sockets; assess the inserts separately.'
    elif facts.socket_contents != 'empty':
        reason += ' Check the socket contents separately.'
    return {
        'status': 'candidate',
        'assessment_scope': 'recoverable_shell',
        'reason': reason,
        'material_stats': [],
        'basis': 'reviewed_build_demand_and_shell_asks',
        'reviewed_at': reviewed,
    }
