"""Single-scroll listings must carry native identity and unambiguous units."""

from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.engine import assess
from tests.pricing.knowledge.assessment.test_supplies import specimen
from tests.pricing.knowledge.test_market_consumables import imported


@pytest.mark.parametrize('name', ['Scroll of Identify', 'Scroll of Town Portal'])
def test_scroll_import_feeds_exact_single_item_comparison(name):
    contract = assess(specimen(name).capture(), profiles=[])['contract']
    result = evaluate(contract, [imported(name, str(i)) for i in range(3)])
    assert len(result['accepted']) == 3
    assert price_from_comparables(result, today=date(2026, 9, 28))['estimate_ist'] == 1  # Synthetic asks.


@pytest.mark.parametrize('amount', [None, True, -1, 2])
def test_scroll_unit_label_cannot_override_actual_quantity(amount):
    contract = assess(specimen('Scroll of Identify').capture(), profiles=[])['contract']
    row = imported('Scroll of Identify', 'bad', amount=amount)
    row['unit_policy'] = 'single_item'
    assert not evaluate(contract, [row])['accepted']


@pytest.mark.parametrize('name', ['Scroll of Knowledge', 'The Black Tower Key', 'Tome of Identify', 'Key', 'Arrows'])
def test_scroll_normalization_does_not_infer_stack_contents_or_quest_identity(name):
    row = imported(name, 'test')
    assert row.get('facet_basis', {}).get('base_code', {}).get('kind') != 'native_single_scroll'


@pytest.mark.parametrize('extra', [[('738', 'bool', True)], [('797', 'string', 'magic')], [('441', 'number', 20)]])
def test_scroll_conflicting_facets_and_modifiers_remain_rejected(extra):
    contract = assess(specimen('Scroll of Identify').capture(), profiles=[])['contract']
    assert not evaluate(contract, [imported('Scroll of Identify', 'bad', extra=extra)])['accepted']
