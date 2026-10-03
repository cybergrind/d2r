"""Captured throwing totals and independently specified base/ethereal outcomes."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = [
    r
    for r in json.loads((Path(__file__).parent / 'fixtures/named_flat_damage.json').read_text())['records']
    if r['name'] in ('Deathbit', "Demon's Arch", 'The Scalper')
]


def contract(observation):
    facts = normalize(observation)
    return NamedHandler().contract(facts, classify(facts)[0])


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
@pytest.mark.parametrize('stat', [21, 22, 159, 160, 253])
@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'raw', 'value'])
def test_throwing_weapon_requires_exact_damage_and_replenishment(record, stat, mutation):
    observation = deepcopy(record['observation'])
    rows = observation['decoded_stats']
    row = next(s for s in rows if s.get('memory_stat', {}).get('id') == stat)
    if mutation == 'missing':
        rows.remove(row)
    elif mutation == 'raw':
        row['memory_stat']['raw'] += 1
    elif mutation == 'value':
        row['value'] += 1
    result, gaps = contract(observation)
    assert (result is not None) is (mutation == 'unchanged'), gaps


@pytest.mark.parametrize(
    ('base', 'ethereal', 'totals', 'maximum_durability', 'accepted'),
    [
        ('Battle Dart', False, (20, 40, 28, 61), 6, True),
        ('Battle Dart', True, (30, 61, 40, 91), 4, True),
        ('Flying Knife', False, (58, 137, 58, 137), 6, True),
        ('Flying Knife', True, (86, 206, 86, 206), 4, False),
    ],
)
def test_deathbit_base_and_ethereal_rounding(base, ethereal, totals, maximum_durability, accepted):
    from inventory_tracking.items.metadata import metadata

    observation = deepcopy(next(r['observation'] for r in RECORDS if r['name'] == 'Deathbit'))
    native = next(b for b in metadata()['bases'].values() if b['name'] == base)
    observation['item'].update(base_code=native['code'], base_name=base, ethereal=ethereal)
    values = dict(zip((21, 22, 159, 160), totals, strict=True)) | {72: 3, 73: maximum_durability}
    for row in observation['decoded_stats']:
        stat = row.get('memory_stat', {}).get('id')
        if stat in values:
            row['value'] = row['memory_stat']['raw'] = values[stat]
    result, gaps = contract(observation)
    assert (result is not None) is accepted, gaps
    if not accepted:
        assert any('ethereal upgrade' in gap for gap in gaps)


@pytest.mark.parametrize('mutation', ['missing_ed', 'conflicting_ed', 'quantity_unit', 'unknown_ethereal'])
def test_throwing_unknown_components_block_comparison(mutation):
    observation = deepcopy(RECORDS[0]['observation'])
    rows = observation['decoded_stats']
    ed = next(r for r in rows if r.get('name') == 'item_damage_percent')
    if mutation == 'missing_ed':
        rows.remove(ed)
    elif mutation == 'conflicting_ed':
        ed['memory_stats'][0]['raw'] += 1
    elif mutation == 'quantity_unit':
        next(r for r in rows if r.get('memory_stat', {}).get('id') == 253)['unit'] = 'quantity'
    elif mutation == 'unknown_ethereal':
        observation['item']['ethereal'] = None
    assert contract(observation)[0] is None


@pytest.mark.parametrize(
    ('base', 'ethereal', 'totals'),
    [
        ('Ceremonial Javelin', False, (79, 155, 79, 212)),
        ('Ceremonial Javelin', True, (106, 206, 106, 293)),
        ('Matriarchal Javelin', False, (115, 212, 130, 248)),
    ],
)
@pytest.mark.parametrize('delta', [0, -1, 1])
def test_titans_flat_damage_is_added_after_base_ethereal_and_percent_scaling(base, ethereal, totals, delta):
    from dataclasses import replace

    from pricing.knowledge.assessment.mechanics.named_throwing import throwing_damage_keys
    from pricing.knowledge.definition_store import catalog
    from tests.pricing.knowledge.assessment.test_family_contracts import facts

    values = dict(zip((21, 22, 159, 160), totals, strict=True)) | {17: 200, 18: 200}
    values[159] += delta
    item = replace(
        facts(base, 'unique', "Titan's Revenge"),
        ethereal=ethereal,
        stats={f'{stat}:0': {'status': 'decoded', 'raw': value, 'value': value} for stat, value in values.items()},
    )
    consumed, gaps = throwing_damage_keys(item, catalog().named['unique', "Titan's Revenge"])
    assert (consumed == {'159:0', '160:0'}) is (delta == 0)
    assert bool(gaps) is (delta != 0)
