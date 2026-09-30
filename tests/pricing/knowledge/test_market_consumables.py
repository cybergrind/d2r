"""Actual potion listing import must feed the same exact comparison as a capture."""

from datetime import date

import pytest

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.engine import assess
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.item_bank.cases.consumables import EXAMPLES
from tests.pricing.knowledge.assessment.item_bank.models import Item


def imported(name, seller, *, amount=1, extra=(), category='misc'):
    props = [
        ('799', 'string', 'softcore'),
        ('800', 'bool', False),
        ('798', 'string', 'PC'),
        ('1854', 'string', 'reign of the warlock'),
    ]
    return normalize_listing(
        {
            'id': seller,
            'seller_id': seller,
            'amount': amount,
            'properties': [{'property_id': k, 'type': t, t: v} for k, t, v in [*props, *extra]],
            'prices': [{'name': 'Ist Rune', 'quantity': 1}],
        },
        name=name,
        category=category,
        source='synthetic-potion-test',
        observed_at='2026-09-28',
        currencies={'ist': 1},
    )


@pytest.mark.parametrize(('code', 'name', '_effect'), EXAMPLES)
def test_all_reviewed_potion_catalogs_import_into_exact_comparisons(code, name, _effect):
    contract = assess(Item(name, 'normal', complete=True).capture(), profiles=[])['contract']
    rows = [imported(name, str(i)) for i in range(3)]
    assert all(row.get('base_code') == code for row in rows)
    compared = evaluate(contract, rows)
    assert len(compared['accepted']) == 3
    price = price_from_comparables(compared, today=date(2026, 9, 28))
    assert price['estimate_ist'] == 1  # Synthetic asks, not real potion prices.


@pytest.mark.parametrize(
    'extra',
    [
        [('797', 'string', 'magic')],
        [('738', 'bool', True)],
        [('402', 'number', 1)],
        [('934', 'string', 'Ber Rune')],
        [('441', 'number', 20)],
    ],
)
def test_conflicting_potion_listing_facets_are_retained_and_rejected(extra):
    contract = assess(Item('Super Healing Potion', 'normal', complete=True).capture(), profiles=[])['contract']
    assert not evaluate(contract, [imported('Super Healing Potion', 'bad', extra=extra)])['accepted']


@pytest.mark.parametrize('amount', [None, True, 2, -1])
def test_single_item_label_cannot_hide_invalid_potion_quantity(amount):
    contract = assess(Item('Super Healing Potion', 'normal', complete=True).capture(), profiles=[])['contract']
    row = imported('Super Healing Potion', 'bad', amount=amount)
    row['unit_policy'] = 'single_item'
    assert not evaluate(contract, [row])['accepted']


@pytest.mark.parametrize(
    ('name', 'category'),
    [
        ('Potion of Life', 'misc'),
        ("Malah's Potion", 'misc'),
        ('Exploding Potion', 'base'),
        ('Super Healing Potion', 'base'),
        ('Ring', 'misc'),
    ],
)
def test_ordinary_potion_rules_do_not_claim_quest_throwing_or_other_catalogs(name, category):
    row = imported(name, 'x', category=category)
    assert row.get('facet_basis', {}).get('rarity', {}).get('kind') != 'native_ordinary_potion'
