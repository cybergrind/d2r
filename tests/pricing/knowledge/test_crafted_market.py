import json
from pathlib import Path

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.test_market import listing


CATALOG = json.loads((Path(__file__).parents[3] / 'pricing/data/appraisal-traderie-catalog.json').read_text())['items']


def crafted(name, **changes):
    entry = next(r for r in CATALOG if r['type'] == 'crafted' and r['name'] == name)
    raw = listing(item_id=entry['id'])
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (797, 402, 738)]
    raw.update(changes)
    return normalize_listing(raw, name=name, category='crafted', source='fixture', currencies={'ist': 1})


@pytest.mark.parametrize('recipe', ['Blood', 'Caster', 'Safety', 'Hit Power'])
@pytest.mark.parametrize('base', ['Ring', 'Amulet'])
def test_crafted_jewelry_catalog_establishes_quality_and_single_base(recipe, base):
    row = crafted(f'{recipe} {base}')
    assert row['rarity'] == 'crafted'
    assert row['name'] == base
    assert row['catalog_name'] == f'{recipe} {base}'
    assert row['base_code'] == next(b['code'] for b in metadata()['bases'].values() if b['name'] == base)
    assert (row['ethereal'], row['sockets'], row['socket_contents']) == (False, 0, 'empty')
    assert row['scope_status'] == 'verified'


def test_crafted_equipment_category_does_not_choose_a_base_tier():
    row = crafted('Blood Gloves')
    assert row['rarity'] == 'crafted'
    assert row['name'] == 'Blood Gloves'
    assert row.get('base_code') is None
    assert row.get('ethereal') is False
    assert row.get('sockets') is None


def test_unverified_catalog_or_conflicting_rarity_is_not_silently_promoted():
    row = crafted('Blood Amulet', item_id='unknown')
    assert row.get('rarity') is None
    raw = listing()['properties']
    row = crafted('Blood Amulet', properties=raw)
    assert row.get('mechanics_conflicts')
    assert row.get('rarity') != 'crafted'


@pytest.mark.parametrize(
    ('key', 'kind', 'value'), [(738, 'bool', True), (402, 'number', 1), (934, 'string', 'Ist Rune')]
)
def test_impossible_crafted_jewelry_facets_remain_conflicts(key, kind, value):
    row = crafted('Caster Amulet', properties=[{'property_id': key, 'type': kind, kind: value}])
    assert row.get('mechanics_conflicts')
    assert row['scope_status'] == 'unknown'


def test_crafted_recipe_listings_can_match_exact_jewelry_contracts():
    from dataclasses import replace
    from datetime import date

    from pricing.knowledge.assessment.comparables import evaluate, price_from_comparables
    from pricing.knowledge.assessment.handlers import HANDLERS
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    item = replace(facts('Amulet', 'crafted'), properties={'418': 55})
    contract, gaps = HANDLERS['affixed'].contract(item, 'jewelry')
    assert contract is not None, gaps
    rows = []
    for i in range(3):
        raw = listing()['properties']
        raw = [p for p in raw if p['property_id'] not in (797, 402, 738)]
        raw.append({'property_id': 418, 'type': 'number', 'number': 55})
        row = crafted('Blood Amulet', id=str(i), seller_id=str(i), properties=raw)
        row['observed_at'] = '2026-09-25'
        rows.append(row)
    estimate = price_from_comparables(evaluate(contract.to_dict(), rows), today=date(2026, 9, 25))
    assert estimate['estimate_ist'] == 2


@pytest.mark.parametrize(
    ('tier', 'base'), [('Normal', 'Heavy Gloves'), ('Exceptional', 'Sharkskin Gloves'), ('Elite', 'Vampirebone Gloves')]
)
def test_crafted_equipment_explicit_tier_resolves_verified_recipe_chain(tier, base):
    row = crafted('Blood Gloves', properties=[{'property_id': 930, 'type': 'string', 'string': tier}])
    assert row['name'] == base
    assert row['catalog_name'] == 'Blood Gloves'
    assert row['base_code'] == next(b['code'] for b in metadata()['bases'].values() if b['name'] == base)
    assert row['sockets'] == 0
    assert row['socket_contents'] == 'empty'
    assert row.get('ethereal') is False


def test_crafted_weapon_tier_does_not_choose_one_base_from_a_weapon_family():
    row = crafted('Blood Weapon', properties=[{'property_id': 930, 'type': 'string', 'string': 'Elite'}])
    assert row['name'] == 'Blood Weapon'
    assert row.get('base_code') is None


@pytest.mark.parametrize('tier', ['elite', 'Unknown', ['Elite'], None])
def test_invalid_or_missing_recipe_tier_does_not_resolve_equipment(tier):
    row = crafted('Blood Gloves', properties=[{'property_id': 930, 'type': 'string', 'string': tier}])
    assert row['name'] == 'Blood Gloves'
    assert row.get('base_code') is None


@pytest.mark.parametrize('name', ['Blood Gloves', 'Caster Body', 'Safety Shield', 'Hit Power Weapon'])
def test_verified_standard_craft_recipe_establishes_nonethereal_output(name):
    row = crafted(name)
    assert row['ethereal'] is False
    assert row['facet_basis']['ethereal']['kind'] == 'crafted_output_mechanics'
    assert row.get('base_code') is None
    impossible = crafted(name, properties=[{'property_id': 738, 'type': 'bool', 'bool': True}])
    assert impossible['mechanics_conflicts']
    assert impossible['properties']['738'] is True
