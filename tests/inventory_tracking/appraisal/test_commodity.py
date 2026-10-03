import pytest

from inventory_tracking.appraisal.presentation import ItemAssessment
from pricing.knowledge.assessment.engine import assess
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize('name', ['Jah Rune', 'Key of Terror', 'Uber Ancient Summon Material Act 1'])
def test_commodity_report_is_unit_price_first_without_equipment_or_duplicate_noise(name):
    capture = Item(name, 'normal', complete=True).capture()
    result = {
        'extraction': capture,
        'assessment': assess(capture, profiles=[]),
        'price_estimate': {
            'estimate_ist': 2,
            'low_ist': 1.5,
            'high_ist': 2.5,
            'sellers': 4,
            'confidence': 'medium',
            'dates': ['2026-10-03'],
        },
        'owned': {'count': 3, 'relation': 'identical', 'kind': name},
    }
    doc = ItemAssessment.from_record({'state': 'complete', 'request_id': 'commodity', 'result': result})
    text = doc.to_text()
    assert 'Unit price: ~2 Ist' in text
    assert 'asks' in text
    assert 'Owned quantity: 3' in text
    for absent in ('Ethereal:', 'Observed stats:', 'already owned', 'variant', 'Normal Uber Ancient'):
        assert absent not in text
    if name.startswith('Uber Ancient'):
        assert "Material: Talic's Anguish" in text
    assert doc.to_rich().plain == text
    assert any('Unit price:' in line.text for line in doc.to_osd())


def test_material_cache_miss_is_not_a_variant_or_liquidity_claim():
    capture = Item('Uber Ancient Summon Material Act 1', 'normal', complete=True).capture()
    result = {
        'extraction': capture,
        'assessment': assess(capture, profiles=[]),
        'price_estimate': {'estimate_ist': None, 'unavailable_reason': 'no_matches'},
    }
    text = ItemAssessment.from_record({'state': 'complete', 'request_id': 'material', 'result': result}).to_text()
    assert 'Unit price: unavailable — no matching scoped commodity quotes.' in text
    assert 'liquid price:' not in text.lower()
    assert 'variant' not in text


def test_bulk_asks_are_labeled_with_quantity_and_do_not_replace_unit_price():
    from inventory_tracking.appraisal.commodity import commodity_lines

    result = {
        'assessment': {'contract': {'policy': 'socket_material'}},
        'extraction': {'item': {'name': 'Jah Rune'}},
        'price_estimate': {'estimate_ist': None, 'unavailable_reason': 'no_matches'},
        'commodity_bulk': [{'quantity': 10, 'estimate': {'estimate_ist': 9}}],
    }
    lines = commodity_lines(result)
    assert 'Unit price: unavailable — no matching scoped commodity quotes.' in lines
    assert 'Bulk 10: ~90 Ist total (~9 each; asks)' in lines


def test_set_quote_is_separate_from_the_component_price():
    from inventory_tracking.appraisal.commodity import commodity_lines

    result = {
        'assessment': {'contract': {'policy': 'quest_material'}},
        'extraction': {'item': {'name': 'Key of Terror'}},
        'price_estimate': {'estimate_ist': None, 'unavailable_reason': 'no_matches'},
        'commodity_set': {
            'name': '3x3 Key Set',
            'quantity_label': '3 of each key; 9 keys total',
            'estimate': {'estimate_ist': 4, 'dates': ['2026-10-03']},
        },
    }
    text = '\n'.join(commodity_lines(result))
    assert 'Unit price: unavailable' in text
    assert 'Complete 3x3 Key Set: ~4 Ist (asks; 3 of each key; 9 keys total)' in text
