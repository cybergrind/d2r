"""Underlying Harlequin Crest demand; defense and inserts do not imply a premium."""

import hashlib
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

from pricing.knowledge.artifacts import read_artifact
from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
from pricing.knowledge.assessment.mechanics.shako_shell import shell_evidence
from pricing.knowledge.assessment.mechanics.socket_evidence import NATIVE_HASHES
from pricing.knowledge.assessment.policies.sources import resolve_pointer
from pricing.knowledge.market import scope_status


ROOT = Path(__file__).resolve().parents[4]
RULES = ROOT / 'pricing/knowledge/assessment/rules/shako_trade.json'
GUIDES = ROOT / 'pricing/data/wp-a-builds.json'
MARKET = ROOT / 'pricing/data/appraisal-market.jsonl'
NATIVE = tuple(ROOT / 'third-parties/d2data/json' / f'{name}.json' for name in NATIVE_HASHES)


def inputs():
    return dict.fromkeys((RULES, GUIDES, MARKET, *NATIVE), 'reviewed Harlequin Crest trade evidence')


@lru_cache(maxsize=2)
def validate(raw, guides, market, native):
    review = json.loads(raw)
    if review['scope'] != 'SC / Non-Ladder / PC / RotW' or review['id'] != 'shako-underlying':
        raise ValueError('Invalid Shako trade scope')
    date.fromisoformat(review['reviewed_at'])
    if hashlib.sha256(guides).hexdigest() != review['guide_sha256']:
        raise ValueError('Shako guide evidence changed')
    for pointer, expected in review['guide_entries'].items():
        if resolve_pointer(json.loads(guides), pointer) != expected or 'Harlequin Crest' not in expected:
            raise ValueError('Invalid Shako guide demand')
    if not review['guide_entries'] or hashlib.sha256(market).hexdigest() != review['market_sha256']:
        raise ValueError('Shako evidence changed')
    ids = review['evidence_ids']
    rows = [row for line in market.splitlines() if (row := json.loads(line))['id'] in ids]
    if len(set(ids)) != len(ids) or len(rows) != len(ids) or {r['id'] for r in rows} != set(ids):
        raise ValueError('Missing or duplicate Shako evidence')
    native_bytes = dict(zip(NATIVE, native, strict=True))
    sellers, low_roll_sellers = set(), set()
    for row in rows:
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
            raise ValueError('Invalid Shako underlying-item evidence')
        date.fromisoformat(row['observed_at'][:10])
        sellers.add(row['seller_id'])
        # A low total puts an upper bound on intrinsic defense despite unknown inserts.
        if row['properties']['1855'] <= 120:
            low_roll_sellers.add(row['seller_id'])
    if len(sellers) < 3 or len(low_roll_sellers) < 3:
        raise ValueError('Insufficient independent Shako low-defense evidence')
    return review['reviewed_at']


def reviewed_date():
    return validate(
        read_artifact(RULES),
        read_artifact(GUIDES),
        read_artifact(MARKET),
        tuple(read_artifact(path) for path in NATIVE),
    )


def assess(facts):
    pending = {'status': 'unresolved', 'reason': 'Harlequin Crest variant needs verification.'}
    if (facts.rarity, facts.name) != ('unique', 'Harlequin Crest'):
        return {}
    definition, _ = resolve_named_definition(facts, identity_only=True)
    defense = facts.stats.get('31:0', {})
    if (
        definition is None
        or facts.base_code != 'uap'
        or facts.identified is not True
        or facts.ethereal is not False
        or facts.capture_complete is not True
        or type(facts.sockets) is not int
        or facts.sockets not in (0, 1)
        or facts.socket_contents not in ('empty', 'filled', 'unknown', None)
        or (facts.socket_contents == 'filled' and facts.sockets == 0)
        or defense.get('status') != 'decoded'
        or type(defense.get('value')) is not int
        or defense['value'] < 98
        or ((facts.socket_contents == 'empty' or facts.sockets == 0) and defense['value'] > 141)
    ):
        return pending
    try:
        reviewed = reviewed_date()
    except OSError, ValueError, KeyError, TypeError:
        return {**pending, 'reason': 'Harlequin Crest trade evidence requires review.'}
    reason = 'Useful fixed skills, life/mana and magic find; low defense still qualifies.'
    if facts.socket_contents != 'empty' and facts.sockets:
        reason += ' Assess inserts separately.'
    return {
        'status': 'candidate',
        'assessment_scope': 'underlying_item',
        'reason': reason,
        'material_stats': [],
        'basis': 'reviewed_build_demand_and_underlying_item_asks',
        'reviewed_at': reviewed,
    }
