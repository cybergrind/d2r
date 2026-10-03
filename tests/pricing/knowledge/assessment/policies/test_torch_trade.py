from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.policies.trade_qualification import assess_trade_qualification
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_unique_charms import TORCH_FIXED
from tests.pricing.knowledge.assessment.item_bank.models import Item


def torch(class_id=0, attributes=10, resists=10):
    rolls = tuple((s, 0, attributes) for s in (0, 1, 2, 3)) + tuple((s, 0, resists) for s in (39, 41, 43, 45))
    return Item('Large Charm', 'unique', 'Hellfire Torch', ((83, class_id, 3), *rolls, *TORCH_FIXED), complete=True)


@pytest.mark.parametrize(('attributes', 'resists'), [(10, 10), (15, 11), (20, 14), (18, 19), (20, 20)])
def test_amazon_has_class_specific_ordinary_demand(attributes, resists):
    result = assess_trade_qualification(normalize(torch(attributes=attributes, resists=resists).capture()))
    assert result['status'] == 'candidate'
    assert 'Amazon' in result['reason']
    assert 'price_estimate' not in result


@pytest.mark.parametrize('class_id', range(1, 8))
def test_other_classes_do_not_borrow_amazon_evidence(class_id):
    assert assess_trade_qualification(normalize(torch(class_id, 20, 20).capture()))['status'] == 'unresolved'


@pytest.mark.parametrize(
    'bad',
    [
        'unknown_class',
        'duplicate_class',
        'wrong_bonus',
        'unknown_capture',
        'unknown_ethereal',
        'unidentified',
        'socketed',
        'unknown_sockets',
        'unknown_contents',
        'unequal_attributes',
        'unequal_resists',
        'missing_attribute',
        'missing_resist',
        'low_attribute',
        'high_resist',
    ],
)
def test_torch_variant_and_compound_requirements(bad):
    item = torch(0, 20, 20)
    raw = item.raw_stats
    if bad == 'unknown_class':
        item = replace(item, raw_stats=tuple(r for r in raw if r[0] != 83))
    elif bad == 'duplicate_class':
        item = replace(item, raw_stats=(*raw, (83, 1, 3)))
    elif bad == 'wrong_bonus':
        item = replace(item, raw_stats=((83, 0, 2), *raw[1:]))
    elif bad in ('unequal_attributes', 'unequal_resists', 'low_attribute', 'high_resist'):
        key, value = {
            'unequal_attributes': (2, 19),
            'unequal_resists': (45, 19),
            'low_attribute': (0, 9),
            'high_resist': (39, 21),
        }[bad]
        item = replace(item, raw_stats=tuple((s, p, value if s == key else v) for s, p, v in raw))
    elif bad in ('missing_attribute', 'missing_resist'):
        key = 0 if bad == 'missing_attribute' else 39
        item = replace(item, raw_stats=tuple(r for r in raw if r[0] != key))
    else:
        changes = {
            'unknown_capture': {'complete': False},
            'unknown_ethereal': {'ethereal': None},
            'unidentified': {'identified': False},
            'socketed': {'sockets': 1},
            'unknown_sockets': {'sockets': None},
            'unknown_contents': {'socket_contents': 'unknown'},
        }[bad]
        item = replace(item, **changes)
    assert assess_trade_qualification(normalize(item.capture()))['status'] == 'unresolved'
