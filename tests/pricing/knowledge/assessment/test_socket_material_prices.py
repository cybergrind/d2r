"""Loose socket materials are fixed identities, not random equipment variants."""

from dataclasses import replace
from datetime import date

import pytest
from dirty_equals import IsPartialDict

from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.engine import assess
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.assessment.item_bank.models import Item


RUNES = [
    'El',
    'Eld',
    'Tir',
    'Nef',
    'Eth',
    'Ith',
    'Tal',
    'Ral',
    'Ort',
    'Thul',
    'Amn',
    'Sol',
    'Shael',
    'Dol',
    'Hel',
    'Io',
    'Lum',
    'Ko',
    'Fal',
    'Lem',
    'Pul',
    'Um',
    'Mal',
    'Ist',
    'Gul',
    'Vex',
    'Ohm',
    'Lo',
    'Sur',
    'Ber',
    'Jah',
    'Cham',
    'Zod',
]
GEMS = [
    f'{grade}{gem}'
    for gem in ('Amethyst', 'Diamond', 'Emerald', 'Ruby', 'Sapphire', 'Topaz', 'Skull')
    for grade in ('Chipped ', 'Flawed ', '', 'Flawless ', 'Perfect ')
]


@pytest.mark.parametrize('name', [*(f'{rune} Rune' for rune in RUNES), *GEMS])
def test_all_native_loose_materials_have_exact_identity_contracts(name):
    result = assess(Item(name, 'normal', complete=True).capture(), profiles=[])
    assert result == IsPartialDict(family='socket_material', quality_policy='socket_material')
    assert result['contract'] == IsPartialDict(
        policy='socket_material',
        name=name,
        rarity='normal',
        ethereal=False,
        sockets=0,
        socket_contents='empty',
        properties={},
    )
    assert result['price_gaps'] == []


@pytest.mark.parametrize(
    'change',
    [
        {'ethereal': True},
        {'ethereal': None},
        {'sockets': 1},
        {'socket_contents': 'filled'},
        {'rarity': 'magic'},
        {'raw_stats': ((39, 0, 20),)},
        {'identified': False},
        {'complete': False},
        {'runeword': 'Spirit'},
    ],
)
def test_loose_material_comparison_preserves_invalid_and_unknown_facts(change):
    result = assess(replace(Item('Ist Rune', 'normal', complete=True), **change).capture(), profiles=[])
    assert result['contract'] is None
    assert result['price_gaps']


def observation(name, seller, *, amount=1, extra=()):
    properties = [
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
            'properties': [{'property_id': k, 'type': t, t: v} for k, t, v in [*properties, *extra]],
            'prices': [{'name': 'Ist Rune', 'quantity': 1}],
        },
        name=name,
        category='runes' if name.endswith(' Rune') else 'gems',
        source='synthetic-test',
        observed_at='2026-09-28',
        currencies={'ist': 1},
    )


@pytest.mark.parametrize('name', ['Ist Rune', 'Perfect Amethyst', 'Chipped Skull'])
def test_single_material_asks_match_but_not_other_identities_bulk_or_impossible_facets(name):
    contract = assess(Item(name, 'normal', complete=True).capture(), profiles=[])['contract']
    good = [observation(name, str(i)) for i in range(3)]
    bad = [
        observation('El Rune' if name.endswith(' Rune') else 'Flawed Ruby', 'other'),
        observation(name, 'bulk', amount=10),
        observation(name, 'eth', extra=[('738', 'bool', True)]),
        observation(name, 'rarity', extra=[('797', 'string', 'magic')]),
        observation(name, 'socket', extra=[('402', 'number', 1)]),
        observation(name, 'affix', extra=[('441', 'number', 45)]),
    ]
    comparison = evaluate(contract, [*good, *bad])
    assert len(comparison['accepted']) == 3
    assert len(comparison['rejected']) == len(bad)
    price = price_from_comparables(comparison, today=date(2026, 9, 28))
    assert price == IsPartialDict(estimate_ist=1, sellers=3, basis='classified_exact_variant_asks')
    assert price_from_comparables(evaluate(contract, good[:2]), today=date(2026, 9, 28))['estimate_ist'] is None


@pytest.mark.parametrize('name', ['Ber Rune', 'Perfect Ruby'])
def test_native_material_runs_through_index_pricing_and_shared_report(tmp_path, name):
    from inventory_tracking.appraisal.text import format_appraisal
    from pricing.knowledge.pipeline import retrieve_draft
    from tests.pricing.knowledge.assessment.test_pipeline_context import database

    rows = [observation(name, str(i)) for i in range(3)]
    result = retrieve_draft(
        Item(name, 'normal', complete=True).capture(), database(tmp_path, rows), as_of=date(2026, 9, 28)
    )
    assert result['price_estimate'] == IsPartialDict(estimate_ist=1, sellers=3)
    text = format_appraisal({'state': 'complete', 'request_id': 'material', 'result': result})
    assert 'Price:' in text
    assert '1 Ist' in text
    assert 'not implemented' not in text
    assert 'No supported stats decoded' not in text
    assert 'No variable rolls' in text


@pytest.mark.parametrize(
    'change',
    [
        {'scope_status': 'unknown'},
        {'observed_at': None},
        {'observed_at': '2026-01-01'},
        {'amount': True},
        {'amount': 2},
        {'amount': 2, 'unit_policy': 'single_item'},
        {'amount': None, 'unit_policy': 'single_item'},
        {'seller_id': None},
        {'evidence_kind': 'buy_offer'},
    ],
)
def test_material_pricing_still_requires_current_scoped_independent_single_unit_asks(change):
    contract = assess(Item('Ist Rune', 'normal', complete=True).capture(), profiles=[])['contract']
    rows = [observation('Ist Rune', str(i)) | change for i in range(3)]
    result = price_from_comparables(evaluate(contract, rows), today=date(2026, 9, 28))
    assert result['estimate_ist'] is None
