import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_class_skills import valid_capture, validate_class_cohorts
from tests.pricing.knowledge.assessment.policies.test_torch_trade import torch


def review():
    evidence = [
        {'id': str(i), 'rarity': 'unique', 'name': 'Hellfire Torch', 'seller_id': str(i), 'properties': {'453': 3}}
        for i in range(3)
    ]
    return {
        'class_skill_ids': [0],
        'market_evidence': evidence,
        'default_status': 'candidate',
        'default_evidence_ids': [str(i) for i in range(3)],
        'bands': [],
    }


def test_native_capture_class_is_required():
    r = review()
    assert valid_capture(r, normalize(torch().capture()))
    for i in range(1, 8):
        assert not valid_capture(r, normalize(torch(i).capture()))
    validate_class_cohorts(r, ('unique', 'Hellfire Torch'))


@pytest.mark.parametrize(
    'bad',
    [
        'other_class',
        'two_classes',
        'unknown_class',
        'wrong_rank',
        'boolean_rank',
        'pooled_classes',
        'same_seller',
        'other_item',
        'duplicate_class_id',
        'invalid_class_id',
    ],
)
def test_class_evidence_cannot_be_pooled_or_forged(bad):
    r = review()
    row = r['market_evidence'][0]
    if bad == 'other_class':
        row['properties'] = {'514': 3}
    elif bad == 'two_classes':
        row['properties']['514'] = 3
    elif bad == 'unknown_class':
        row['properties'] = {}
    elif bad == 'wrong_rank':
        row['properties']['453'] = 2
    elif bad == 'boolean_rank':
        row['properties']['453'] = True
    elif bad == 'pooled_classes':
        r['class_skill_ids'] = [0, 1]
        row['properties'] = {'514': 3}
    elif bad == 'same_seller':
        for row in r['market_evidence']:
            row['seller_id'] = 'one'
    elif bad == 'other_item':
        row['name'] = 'Annihilus'
    elif bad == 'duplicate_class_id':
        r['class_skill_ids'] = [0, 0]
    else:
        r['class_skill_ids'] = [8]
    with pytest.raises(ValueError, match=r'[Tt]rade'):
        validate_class_cohorts(r, ('unique', 'Hellfire Torch'))


def test_integral_json_class_bonus_is_not_an_unknown_class():
    r = review()
    for row in r['market_evidence']:
        row['properties']['453'] = 3.0
    validate_class_cohorts(r, ('unique', 'Hellfire Torch'))
