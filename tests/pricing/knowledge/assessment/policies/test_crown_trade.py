"""Crown socket utility must not become a fabricated intrinsic-roll premium."""

from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


def crown(defense=349, resistance=20, reduction=10):
    return Item(
        'Corona',
        'unique',
        'Crown of Ages',
        (
            (31, 0, defense),
            (36, 0, reduction),
            (127, 0, 1),
            (99, 0, 30),
            *((s, 0, resistance) for s in (39, 41, 43, 45)),
        ),
        sockets=2,
        complete=True,
    )


@pytest.mark.parametrize('rolls', [(349, 20, 10), (375, 25, 13), (399, 30, 15)])
def test_two_socket_crown_is_a_candidate_without_an_unsupported_premium(rolls):
    result = assess_trade_qualification(normalize(crown(*rolls).capture()))
    assert result['status'] == 'candidate'
    assert result['assessment_scope'] == 'recoverable_shell'
    assert 'Two sockets' in result['reason']
    assert 'price' not in result


@pytest.mark.parametrize(
    'changes',
    [
        {'sockets': 1},
        {'sockets': 0},
        {'sockets': 3},
        {'sockets': None},
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
        {'capture_complete': False},
        {'stats': {}},
        {'base_code': 'invalid'},
    ],
)
def test_missing_or_incompatible_facts_do_not_inherit_two_socket_demand(changes):
    result = assess_trade_qualification(replace(normalize(crown().capture()), **changes))
    assert result['status'] == 'unresolved'


@pytest.mark.parametrize(
    'rolls', [(348, 20, 10), (400, 20, 10), (349, 19, 10), (349, 31, 10), (349, 20, 9), (349, 20, 16)]
)
def test_empty_crown_requires_legal_native_rolls(rolls):
    assert assess_trade_qualification(normalize(crown(*rolls).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize('contents', ['filled', 'unknown', None])
def test_inserted_bonuses_are_not_intrinsic_premium_rolls(contents):
    facts = replace(normalize(crown(349, 20, 26).capture()), socket_contents=contents)
    result = assess_trade_qualification(facts)
    assert result['status'] == 'candidate'
    assert 'inserts separately' in result['reason']


def test_empty_crown_cannot_have_unequal_native_all_resistances():
    facts = normalize(crown().capture())
    stats = {**facts.stats, '39:0': {**facts.stats['39:0'], 'value': 21}}
    assert assess_trade_qualification(replace(facts, stats=stats))['status'] == 'unresolved'


@pytest.mark.parametrize(
    'mutation',
    [
        'hardcore',
        'ladder',
        'seller',
        'date',
        'socket',
        'ethereal',
        'defense',
        'conflicting-reduction',
        'duplicate',
        'guide',
        'native',
    ],
)
def test_invalid_market_or_native_evidence_cannot_publish(mutation):
    import hashlib
    import json

    from pricing.knowledge.assessment.policies import crown_trade

    rule = json.loads(crown_trade.RULES.read_bytes())
    rows = [
        r
        for line in crown_trade.MARKET.read_bytes().splitlines()
        if (r := json.loads(line))['id'] in rule['evidence_ids']
    ]
    guides = crown_trade.GUIDES.read_bytes()
    native = tuple(p.read_bytes() for p in crown_trade.NATIVE)
    if mutation == 'hardcore':
        rows[0]['properties']['799'] = 'hardcore'
    elif mutation == 'ladder':
        rows[0]['properties']['800'] = True
    elif mutation == 'seller':
        for row in rows:
            row['seller_id'] = 'one seller'
    elif mutation == 'date':
        rows[0]['observed_at'] = 'unknown'
    elif mutation == 'socket':
        rows[0]['properties']['402'] = 1
    elif mutation == 'ethereal':
        rows[0]['ethereal'] = True
    elif mutation == 'defense':
        rows[0]['properties']['399'] = rows[0]['properties'].pop('1855')
    elif mutation == 'conflicting-reduction':
        rows[0]['properties']['413'] = 99
    elif mutation == 'duplicate':
        rows.append(rows[0])
    elif mutation == 'guide':
        guides += b'\n'
    else:
        native = (native[0] + b'\n', *native[1:])
    market = b'\n'.join(json.dumps(row).encode() for row in rows)
    rule['market_sha256'] = hashlib.sha256(market).hexdigest()
    with pytest.raises(ValueError, match=r'Crown|Invalid isoformat'):
        crown_trade.validate(json.dumps(rule).encode(), guides, market, native)
