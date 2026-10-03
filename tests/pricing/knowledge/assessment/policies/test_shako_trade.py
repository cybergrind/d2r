"""Defense is not a minimum trade gate for an ordinary nonethereal Shako."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def shako(defense=98):
    return Item(
        'Shako',
        'unique',
        'Harlequin Crest',
        (
            (31, 0, defense),
            (127, 0, 2),
            (80, 0, 50),
            (36, 0, 10),
            (216, 0, 12 * 256),
            (217, 0, 12 * 256),
            (0, 0, 2),
            (1, 0, 2),
            (2, 0, 2),
            (3, 0, 2),
        ),
        complete=True,
    )


@pytest.mark.parametrize('defense', [98, 99, 120, 130, 140, 141])
def test_ordinary_shako_defense_rolls_are_candidates_not_automatic_premiums(defense):
    result = assess_trade_qualification(normalize(shako(defense).capture()))
    assert result['status'] == 'candidate'
    assert result['assessment_scope'] == 'underlying_item'
    assert 'fixed' in result['reason']
    assert result['material_stats'] == []
    assert 'price_estimate' not in result


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
        {'sockets': 2},
        {'sockets': None},
        {'capture_complete': False},
        {'base_code': 'invalid'},
        {'stats': {}},
    ],
)
def test_unverified_or_impossible_shako_cannot_inherit_ordinary_trade_demand(changes):
    result = assess_trade_qualification(replace(normalize(shako().capture()), **changes))
    assert result.get('status') != 'candidate'


@pytest.mark.parametrize('defense', [97, 142, 147])
def test_empty_shako_requires_legal_native_defense(defense):
    assert assess_trade_qualification(normalize(shako(defense).capture())).get('status') != 'candidate'


@pytest.mark.parametrize('contents', ['filled', 'unknown'])
def test_inserted_item_value_is_not_part_of_shako_trade_claim(contents):
    facts = replace(normalize(shako(180).capture()), sockets=1, socket_contents=contents)
    result = assess_trade_qualification(facts)
    assert result['status'] == 'candidate'
    assert 'inserts separately' in result['reason']


def test_filled_zero_socket_shako_is_contradictory():
    facts = replace(normalize(shako().capture()), socket_contents='filled')
    assert assess_trade_qualification(facts).get('status') != 'candidate'


@pytest.fixture
def evidence():
    import json

    from pricing.knowledge.assessment.policies import shako_trade

    rule = json.loads(shako_trade.RULES.read_bytes())
    rows = [
        r
        for line in shako_trade.MARKET.read_bytes().splitlines()
        if (r := json.loads(line))['id'] in rule['evidence_ids']
    ]
    return rule, rows, shako_trade.GUIDES.read_bytes(), tuple(p.read_bytes() for p in shako_trade.NATIVE)


@pytest.mark.parametrize(
    'mutation', ['hardcore', 'ladder', 'duplicate', 'seller', 'date', 'defense', 'guide', 'native']
)
def test_invalid_evidence_cannot_publish_shako_trade_claim(evidence, mutation):
    import hashlib
    import json

    from pricing.knowledge.assessment.policies import shako_trade

    rule, rows, guides, native = evidence
    if mutation == 'hardcore':
        rows[0]['properties']['799'] = 'hardcore'
    elif mutation == 'ladder':
        rows[0]['properties']['800'] = True
    elif mutation == 'duplicate':
        rows.append(rows[0])
    elif mutation == 'seller':
        for row in rows:
            row['seller_id'] = 'one-seller'
    elif mutation == 'date':
        rows[0]['observed_at'] = 'unknown'
    elif mutation == 'defense':
        for row in rows:
            row['properties']['1855'] = 141
    elif mutation == 'guide':
        guides += b'\n'
    else:
        native = (native[0] + b'\n', *native[1:])
    market = b'\n'.join(json.dumps(row).encode() for row in rows)
    rule['market_sha256'] = hashlib.sha256(market).hexdigest()
    with pytest.raises(ValueError, match=r'Shako|Invalid isoformat'):
        shako_trade.validate(json.dumps(rule).encode(), guides, market, native)
