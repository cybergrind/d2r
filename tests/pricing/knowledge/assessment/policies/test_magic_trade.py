"""Trade interest in JMOD must survive class/payload differences, not bad variants."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from pricing.knowledge.assessment.policies import magic_trade
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification


def facts(**changes):
    return SimpleNamespace(
        **{
            'name': "Jeweler's Monarch of Deflecting",
            'rarity': 'magic',
            'base_code': 'uit',
            'identified': True,
            'ethereal': False,
            'sockets': 4,
            'socket_contents': 'empty',
            'capture_complete': True,
            'properties': {'446': 42},
            'stats': {'20:0': {'status': 'decoded', 'value': 42}, '102:0': {'status': 'decoded', 'value': 30}},
            **changes,
        }
    )


@pytest.mark.parametrize('contents', ['empty', 'filled', None])
def test_jmod_is_a_trade_base_without_pricing_its_payload(contents):
    result = assess_trade_qualification(facts(socket_contents=contents))
    assert result['status'] == 'candidate'
    assert result['assessment_scope'] == 'recoverable_shell'
    assert 'JMOD' in result['reason']
    assert 'price' not in result


@pytest.mark.parametrize(
    'changes',
    [
        {'identified': False},
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': None},
        {'sockets': 3},
        {'capture_complete': False},
        {'stats': {}},
        {'stats': {'20:0': {'status': 'decoded', 'value': 42}, '102:0': {'status': 'decoded', 'value': 50}}},
    ],
)
def test_unverified_or_different_variants_do_not_inherit_the_trade_claim(changes):
    assert assess_trade_qualification(facts(**changes)).get('status') != 'candidate'


def test_other_magic_shields_do_not_inherit_jmod_demand():
    assert assess_trade_qualification(facts(base_code='invalid-base')) == {}


@pytest.fixture
def review_inputs():
    rule = json.loads(magic_trade.RULES.read_bytes())
    rows = [
        row
        for line in magic_trade.MARKET.read_bytes().splitlines()
        if (row := json.loads(line))['id'] in rule['evidence_ids']
    ]
    return rule, rows, magic_trade.GUIDES.read_bytes(), tuple(p.read_bytes() for p in magic_trade.NATIVE)


def validate_inputs(parts):
    rule, rows, guide, native = parts
    market = b'\n'.join(json.dumps(row).encode() for row in rows)
    rule['market_sha256'] = hashlib.sha256(market).hexdigest()
    return magic_trade.validate(json.dumps(rule).encode(), guide, market, native)


def test_review_uses_independent_sc_nonladder_shell_evidence(review_inputs):
    assert validate_inputs(review_inputs) == '2026-10-02'


@pytest.mark.parametrize('mutation', ['hardcore', 'ladder', 'sellers', 'date', 'defense', 'fbr', 'native', 'guide'])
def test_publication_rejects_invalid_magic_trade_evidence(review_inputs, mutation):
    rule, rows, guide, native = review_inputs
    if mutation == 'hardcore':
        rows[0]['properties']['799'] = 'hardcore'
    elif mutation == 'ladder':
        rows[0]['properties']['800'] = True
    elif mutation == 'sellers':
        for row in rows:
            row['seller_id'] = 'same-seller'
    elif mutation == 'date':
        rows[0]['observed_at'] = 'not-a-date'
    elif mutation == 'defense':
        rows[0]['properties']['399'] = rows[0]['properties'].pop('1855')
    elif mutation == 'fbr':
        rows[0]['properties']['449'] = 50
    elif mutation == 'native':
        native = (native[0] + b'\n', *native[1:])
    else:
        guide += b'\n'
    with pytest.raises(ValueError, match=r'JMOD|Magic trade|Invalid isoformat'):
        validate_inputs((rule, rows, guide, native))
