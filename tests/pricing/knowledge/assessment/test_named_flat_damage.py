"""Nonweapon damage bonuses populate three native representations together."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from pricing.knowledge.assessment.registry import classify


RECORDS = json.loads((Path(__file__).parent / 'fixtures/named_flat_damage.json').read_text())['records']
ARMOR = [r for r in RECORDS if r['name'] in ('Bloodfist', "Iratha's Cord", 'Duskdeep', 'Razortail')]
WEAPONS = [r for r in RECORDS if r not in ARMOR]


@pytest.mark.parametrize('record', ARMOR, ids=lambda r: r['name'])
@pytest.mark.parametrize('component', [0, 1, 2])
@pytest.mark.parametrize('mutation', ['unchanged', 'missing', 'raw', 'value'])
def test_armor_flat_damage_requires_all_three_native_values(record, component, mutation):
    observation = deepcopy(record['observation'])
    ids = (21, 23, 159) if record['name'] in ('Bloodfist', "Iratha's Cord") else (22, 24, 160)
    rows = observation['decoded_stats']
    row = next(s for s in rows if s.get('memory_stat', {}).get('id') == ids[component])
    if mutation == 'missing':
        rows.remove(row)
    elif mutation == 'raw':
        row['memory_stat']['raw'] += 1
    elif mutation == 'value':
        row['value'] += 1
    facts = normalize(observation)
    contract, gaps = NamedHandler().contract(facts, classify(facts)[0])
    assert (contract is not None) is (mutation == 'unchanged'), gaps
    if mutation != 'unchanged':
        assert gaps


@pytest.mark.parametrize('record', WEAPONS, ids=lambda r: r['name'])
def test_throwing_weapon_totals_are_not_treated_as_flat_armor_bonuses(record):
    from pricing.knowledge.assessment.handlers.definitions import resolve_named_definition
    from pricing.knowledge.assessment.mechanics.named_flat_damage import fixed_armor_damage_keys

    facts = normalize(record['observation'])
    definition, gaps = resolve_named_definition(facts)
    assert not gaps
    assert fixed_armor_damage_keys(facts, definition, classify(facts)[0]) == (set(), [])
