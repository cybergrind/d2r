"""Ordinary potion utility is inherent, not an unreadable affix or equipment role."""

from dataclasses import replace

import pytest
from dirty_equals import IsPartialDict

from inventory_tracking.appraisal.text import format_appraisal
from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.assessment.engine import assess
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.item_bank.models import Item


@pytest.mark.parametrize(
    ('name', 'effect'),
    [
        ('Minor Healing Potion', 'Restores life over time'),
        ('Light Healing Potion', 'Restores life over time'),
        ('Healing Potion', 'Restores life over time'),
        ('Greater Healing Potion', 'Restores life over time'),
        ('Super Healing Potion', 'Restores life over time'),
        ('Thawing Potion', '+50% cold resistance'),
        ('Antidote Potion', '+50% poison resistance'),
    ],
)
def test_potion_has_practical_utility_and_exact_comparison_contract(name, effect):
    extraction = Item(name, 'normal', complete=True).capture()
    result = retrieve_draft(extraction, DEFAULT_DATABASE)
    assert result['assessment'] == IsPartialDict(family='consumable', quality_policy='consumable')
    utility = result['assessment']['utility']
    assert utility['status'] == 'usable'
    assert any(effect in line for line in utility['effects'])
    assert any('mercenary' in line for line in utility['uses'])
    assert utility['variable_rolls'] is False
    assert result['assessment']['contract']['policy'] == 'consumable'
    text = format_appraisal({'state': 'complete', 'request_id': 'potion-bank', 'result': result})
    assert effect in text
    assert 'No supported stats decoded' not in text
    assert 'comparison policy is not implemented' not in text


@pytest.mark.parametrize(
    'change',
    [
        {'ethereal': True},
        {'sockets': 1},
        {'socket_contents': 'filled'},
        {'rarity': 'magic'},
        {'identified': False},
        {'raw_stats': ((39, 0, 50),)},
    ],
)
def test_potions_with_impossible_or_unverified_facets_are_not_silently_normalized(change):
    item = replace(Item('Thawing Potion', 'normal', complete=True), **change)
    result = assess(item.capture(), profiles=[])
    assert result.get('utility', {}).get('status') != 'usable'
    assert result['contract'] is None


def test_unknown_capture_preserves_conditional_use_without_a_price_contract():
    item = Item('Antidote Potion', 'normal', complete=False)
    result = assess(item.capture(), profiles=[])
    assert result['utility']['status'] == 'review'
    assert result['contract'] is None


def test_potion_definition_does_not_turn_other_misc_items_into_potions():
    result = assess(Item('El Rune', 'normal', complete=True).capture(), profiles=[])
    assert 'utility' not in result
    assert result['family'] != 'consumable'


def test_potion_market_comparisons_reject_other_grades_bulk_and_wrong_scope():
    from datetime import date

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
    from tests.pricing.knowledge.assessment.test_comparables import listing

    result = assess(Item('Super Healing Potion', 'normal', complete=True).capture(), profiles=[])
    contract = result['contract']
    rows = [
        listing(
            str(i),
            name=contract['name'],
            amount=1,
            base_code=contract['base_code'],
            rarity='normal',
            sockets=0,
            properties={},
            ask_ist=i / 100,
        )
        for i in (1, 2, 3)
    ]
    bad = [
        {**rows[0], 'name': 'Greater Healing Potion', 'listing_id': 'other-grade'},
        {**rows[0], 'unit_policy': 'bulk', 'listing_id': 'bulk'},
        {**rows[0], 'scope_status': 'rejected', 'listing_id': 'ladder'},
        {**rows[0], 'base_code': None, 'listing_id': 'unknown-identity'},
    ]
    evaluated = evaluate(contract, [*rows, *bad])
    assert len(evaluated['accepted']) == 3
    assert len(evaluated['rejected']) == 4
    price = price_from_comparables(evaluated, today=date(2026, 9, 24))
    assert price['estimate_ist'] == 0.02  # Synthetic single-unit examples, not actual market evidence.
    assert price_from_comparables(evaluate(contract, rows[:1]), today=date(2026, 9, 24))['estimate_ist'] is None


@pytest.mark.parametrize(
    ('name', 'effect', 'recipient'),
    [
        ('Minor Mana Potion', 'Restores mana over time', 'player'),
        ('Light Mana Potion', 'Restores mana over time', 'player'),
        ('Mana Potion', 'Restores mana over time', 'player'),
        ('Greater Mana Potion', 'Restores mana over time', 'player'),
        ('Super Mana Potion', 'Restores mana over time', 'player'),
        ('Rejuvenation Potion', 'Instantly restores 35%', 'mercenary'),
        ('Full Rejuvenation Potion', 'Instantly restores 100%', 'mercenary'),
        ('Stamina Potion', 'Restores stamina', 'player'),
    ],
)
def test_remaining_potions_have_recipient_specific_effects(name, effect, recipient):
    result = retrieve_draft(Item(name, 'normal', complete=True).capture(), DEFAULT_DATABASE)
    utility = result['assessment']['utility']
    assert utility['status'] == 'usable'
    assert any(effect in line for line in utility['effects'])
    assert any(recipient in line for line in utility['uses'])
    assert result['assessment']['contract']['policy'] == 'consumable'
    if 'Mana' in name or 'Stamina' in name:
        assert not any('mercenary' in line for line in utility['uses'])
