from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.named_baselines import assess_tier
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize('base', ['Ceremonial Javelin', 'Matriarchal Javelin'])
@pytest.mark.parametrize(
    ('ed', 'leech', 'expected'),
    [
        (150, 9, 'unresolved'),
        (189, 9, 'unresolved'),
        (190, 5, 'premium'),
        (199, 9, 'premium'),
        (200, 5, 'premium'),
        (200, 9, 'premium'),
    ],
)
def test_titan_ethereal_ed_threshold_does_not_turn_lower_rolls_into_worthless(base, ed, leech, expected):
    item = Item(base, 'unique', "Titan's Revenge", ((17, 0, ed), (18, 0, ed), (60, 0, leech)), ethereal=True)
    result = assess_trade_qualification(normalize(item.capture()))
    if base == 'Matriarchal Javelin' and ed < 200:
        expected = 'unresolved'
    assert result['status'] == expected
    tier = assess_tier(normalize(item.capture()))['tier']
    assert (tier == 'high') is (expected == 'premium')
    assert 'price_estimate' not in result
    if expected == 'unresolved':
        assert 'lower' in result['reason'].lower()


@pytest.mark.parametrize(
    'stats',
    [
        ((17, 0, 200), (60, 0, 9)),
        ((17, 0, 200), (18, 0, 199), (60, 0, 9)),
        ((17, 0, 200), (18, 0, 200)),
        ((17, 0, 200), (18, 0, 200), (60, 0, 10)),
    ],
)
def test_titan_missing_mismatched_or_illegal_material_rolls_never_qualify(stats):
    facts = normalize(Item('Ceremonial Javelin', 'unique', "Titan's Revenge", stats, ethereal=True).capture())
    assert assess_trade_qualification(facts)['status'] == 'unresolved'
    if not {17, 18} <= {row[0] for row in stats} or stats[0][2] != stats[1][2]:
        assert assess_tier(facts)['tier'] != 'high'


@pytest.mark.parametrize(
    'changes', [{'ethereal': False}, {'ethereal': None}, {'sockets': None}, {'sockets': 1}, {'identified': False}]
)
def test_titan_unknown_or_unsupported_variants_do_not_inherit_premium(changes):
    item = Item(
        'Ceremonial Javelin', 'unique', "Titan's Revenge", ((17, 0, 200), (18, 0, 200), (60, 0, 9)), ethereal=True
    )
    assert assess_trade_qualification(replace(normalize(item.capture()), **changes))['status'] == 'unresolved'


def test_unresolved_default_cannot_be_relabelled_as_evidence_free_trade_candidate():
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    review = next(r for r in document['policies'] if r['name'] == "Titan's Revenge")['trade_qualification']
    assert review['default_evidence_ids'] == []
    review['default_status'] = 'candidate'
    with pytest.raises(ValueError, match='trade band evidence'):
        _policies(json.dumps(document).encode())


def test_native_and_upgraded_cohorts_are_reviewed_independently():
    import json

    from pricing.knowledge.assessment.policies.named_tiers import RULES, _policies

    document = json.loads(RULES.read_bytes())
    review = next(r for r in document['policies'] if r['name'] == "Titan's Revenge")['trade_qualification']
    assert len(review['bands']) == 2
    indexed = {r['id']: r for r in review['market_evidence']}
    for band in review['bands']:
        rows = [indexed[key] for key in band['evidence_ids']]
        assert len({r['base_code'] for r in rows}) == 1
        assert len({r['seller_id'] for r in rows}) >= 3
    # Moving a listed original-base ask into the upgraded band must fail validation.
    moved = review['bands'][0]['evidence_ids'].pop()
    review['bands'][1]['evidence_ids'].append(moved)
    with pytest.raises(ValueError, match='Trade evidence does not match'):
        _policies(json.dumps(document).encode())
