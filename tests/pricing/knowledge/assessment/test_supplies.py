"""Ordinary supplies preserve quantity and do not absorb quest/unused catalogs."""

from dataclasses import replace

import pytest

from inventory_tracking.appraisal.text import format_appraisal
from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.assessment.engine import assess
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.item_bank.models import Item


SUPPLIES = (
    ('Scroll of Identify', None, 'Identifies'),
    ('Scroll of Town Portal', None, 'portal'),
    ('Tome of Identify', 12, '12/20'),
    ('Tome of Town Portal', 0, '0/20'),
    ('Key', 5, '5/12'),
    ('Arrows', 250, '250/500'),
    ('Bolts', 125, '125/500'),
)


def specimen(name, quantity=None, **kwargs):
    return Item(name, 'normal', raw_stats=() if quantity is None else ((70, 0, quantity),), complete=True, **kwargs)


@pytest.mark.parametrize(('name', 'quantity', 'text'), SUPPLIES)
def test_supply_native_utility_survives_full_report(name, quantity, text):
    result = retrieve_draft(specimen(name, quantity).capture(), DEFAULT_DATABASE)
    assessment = result['assessment']
    assert assessment['family'] == 'supply'
    assert assessment['quality_policy'] == 'supply'
    assert assessment['utility']['status'] == 'usable'
    assert assessment['utility']['variable_rolls'] is False
    rendered = format_appraisal({'state': 'complete', 'request_id': 'supplies', 'result': result})
    assert 'Supply use:' in rendered
    assert text in rendered
    assert 'No supported stats decoded' not in rendered
    if quantity is None:
        assert assessment['contract']['policy'] == 'supply'
    else:
        # A listing's number of stacks is not the count inside a captured stack.
        assert assessment['contract'] is None
        assert any('listing quantity' in g for g in assessment['price_gaps'])


@pytest.mark.parametrize(('name', 'quantity'), [('Key', 13), ('Arrows', 501), ('Bolts', -1), ('Tome of Identify', 21)])
def test_quantity_outside_native_capacity_remains_a_gap(name, quantity):
    result = assess(specimen(name, quantity).capture(), profiles=[])
    assert result['utility']['status'] == 'review'
    assert result['contract'] is None
    assert any('quantity' in g.lower() for g in result['utility']['gaps'])


@pytest.mark.parametrize('name', ['Arrows', 'Bolts', 'Key', 'Tome of Identify', 'Tome of Town Portal'])
def test_missing_stack_quantity_is_not_inferred_from_complete_stat_array(name):
    result = assess(specimen(name).capture(), profiles=[])
    assert result['utility']['status'] == 'review'
    assert result['contract'] is None
    assert result['utility']['quantity'] is None


@pytest.mark.parametrize(
    'change', [{'ethereal': True}, {'raw_stats': ((39, 0, 20),)}, {'sockets': 1}, {'complete': False}]
)
def test_impossible_or_unknown_supply_facets_do_not_form_price_contract(change):
    item = replace(specimen('Scroll of Identify'), **change)
    result = assess(item.capture(), profiles=[])
    assert result['utility']['status'] == 'review'
    assert result['contract'] is None


@pytest.mark.parametrize('name', ['Scroll of Knowledge', 'The Black Tower Key'])
def test_quest_and_unused_catalogs_do_not_inherit_ordinary_supply_rules(name):
    result = assess(specimen(name).capture(), profiles=[])
    assert result.get('utility') is None
    assert result['contract'] is None
