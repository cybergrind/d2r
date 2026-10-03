"""Numeric Gore Rider comparisons retain exact rolls and scope after variant proof."""

import json
from copy import deepcopy
from datetime import date
from functools import lru_cache
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.item_bank.cases.gore_rider_trade import boots
from tests.pricing.knowledge.assessment.item_bank.cases.gore_rider_upgraded_trade import upgraded


@lru_cache
def listings():
    return [
        r
        for r in map(json.loads, Path('pricing/data/appraisal-market.jsonl').read_text().splitlines())
        if r.get('name') == 'Gore Rider'
    ]


def contract(item=None):
    result, gaps = NamedHandler().contract(normalize((item or boots(200)).capture()), 'accessory')
    assert result is not None, gaps
    return result.to_dict()


def test_real_original_perfect_roll_has_three_exact_sellers_without_changing_raw_rows():
    rows = listings()
    before = deepcopy(rows)
    compared = evaluate(contract(), rows)
    price = price_from_comparables(compared, today=date(2026, 10, 2))
    assert price['sellers'] == 3
    assert price['estimate_ist'] == 9.32
    assert price['basis'] == 'classified_exact_variant_asks'
    assert all(r['base_code'] == 'xhb' and r['ethereal'] is False for r in compared['accepted'])
    assert rows == before
    assert all(r['facet_basis']['ethereal']['kind'] == 'reviewed_named_defense' for r in compared['accepted'])


@pytest.mark.parametrize(('base_defense', 'sellers'), [(65, 1), (69, 2), (70, 1), (71, 1)])
def test_upgraded_total_defense_cohorts_are_not_merged(base_defense, sellers):
    compared = evaluate(contract(upgraded(base_defense=base_defense)), listings())
    price = price_from_comparables(compared, today=date(2026, 10, 2))
    assert price['sellers'] == sellers
    assert price['estimate_ist'] is None
    assert all(r['properties']['1855'] == base_defense * 3 for r in compared['accepted'])


@pytest.mark.parametrize(
    'mutation',
    [
        'different-ed',
        'different-defense',
        'wrong-base',
        'ethereal',
        'unknown-defense',
        'ladder',
        'hardcore',
        'socketed',
        'extra-modifier',
        'wrong-tier',
        'ambiguous-quantity',
        'contradictory-unit',
        'conflicting-ethereal',
        'conflicting-upgrade',
    ],
)
def test_proof_does_not_relax_other_comparison_requirements(mutation):
    row = deepcopy(next(r for r in listings() if r['id'] == '9988c7c60ef936f2d04877f9'))
    if mutation == 'different-ed':
        row['properties']['425'] = 199
    elif mutation == 'different-defense':
        row['properties']['1855'] = 161
    elif mutation == 'wrong-base':
        row['base_code'] = 'uhb'
    elif mutation == 'ethereal':
        row['ethereal'] = True
    elif mutation == 'unknown-defense':
        row['properties'].pop('1855')
    elif mutation == 'ladder':
        row['properties']['800'] = True
    elif mutation == 'hardcore':
        row['properties']['799'] = 'hardcore'
    elif mutation == 'socketed':
        row['sockets'] = 1
    elif mutation == 'extra-modifier':
        row['properties']['427'] = 30
    elif mutation == 'wrong-tier':
        row['properties']['930'] = 'Normal'
    elif mutation == 'contradictory-unit':
        row['amount'] = 4
    elif mutation == 'conflicting-ethereal':
        row['ethereal'] = False
        row['properties']['738'] = True
    elif mutation == 'conflicting-upgrade':
        row['base_upgrade'] = False
        row['properties']['1216'] = True
    else:
        row['unit_policy'] = 'ambiguous'
        row['amount'] = 4
    compared = evaluate(contract(), [row])
    assert not compared['accepted']
    assert compared['rejected'][0]['reasons']


def test_old_or_duplicate_seller_asks_cannot_make_a_price():
    compared = evaluate(contract(), listings())
    assert price_from_comparables(compared, today=date(2026, 10, 19))['estimate_ist'] is None
    same_seller = [r for r in compared['accepted'] if r['seller_id'] == '4119538503']
    assert len(same_seller) > 1
    price = price_from_comparables(evaluate(contract(), same_seller), today=date(2026, 10, 2))
    assert price['sellers'] == 1
    assert price['estimate_ist'] is None
