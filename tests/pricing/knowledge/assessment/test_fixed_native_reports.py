"""Real named observations reach the published-data pipeline and readable report."""

import json
from pathlib import Path

import pytest

from inventory_tracking.appraisal.text import format_appraisal
from pricing.knowledge.pipeline import retrieve_draft
from pricing.knowledge.publication import current_generation
from pricing.knowledge.published_runtime import load_runtime, published_snapshot


FIXTURES = Path(__file__).parent / 'fixtures'
CASES = [
    ('named_variable_triggers.json', 'Stormspire', '2% Chance to cast level 20 Charged Bolt when struck'),
    ('named_cold_duration.json', 'Hellrack', 'Adds 63-324 Cold Damage'),
    ('named_flat_damage.json', 'Deathbit', 'Throw Damage: 28-61'),
    ('named_flat_damage.json', "Demon's Arch", 'Throw Damage: 109-169'),
    ('named_flat_damage.json', 'The Scalper', 'Throw Damage: 47-86'),
    ('named_flat_damage.json', 'Bloodfist', '+5 to Minimum Damage'),
    ('named_flat_damage.json', "Iratha's Cord", '+5 to Minimum Damage'),
    ('named_flat_damage.json', 'Duskdeep', '+8 to Maximum Damage'),
    ('named_flat_damage.json', 'Razortail', '+10 to Maximum Damage'),
    ('named_special_effects.json', 'Tomb Reaver', '10% Reanimate as: Returned'),
    ('named_special_effects.json', "M'avina's Caster", 'Fires Magic Arrows (Level 1)'),
    ('named_special_effects.json', 'Gorefoot', '+2 to Leap (Barbarian Only)'),
    ('named_magic_damage.json', "Ginther's Rift", 'Adds 50-120 Magic Damage'),
    ('named_magic_damage.json', 'Stoneraven', 'Adds 101-187 Magic Damage'),
    ('named_fixed_skills.json', "Blackbog's Sharp", '+5 to Poison Dagger (Necromancer Only)'),
    ('named_fixed_skills.json', 'Hand of Blessed Light', '+4 to Holy Bolt (Paladin Only)'),
    ('named_fixed_skills.json', 'Blastbark', '+2 to Exploding Arrow (Amazon Only)'),
    ('named_fixed_skills.json', 'Heart Carver', '+4 to Find Potion (Barbarian Only)'),
]


@pytest.fixture(scope='module')
def runtime():
    return load_runtime(current_generation('pricing/data/generations'))


@pytest.mark.parametrize(('fixture', 'name', 'line'), CASES)
def test_fixed_native_stats_survive_published_data_report(runtime, fixture, name, line):
    records = json.loads((FIXTURES / fixture).read_text())['records']
    observation = next(r['observation'] for r in records if r['name'] == name)
    with published_snapshot(runtime):
        result = retrieve_draft(observation, runtime.database)
        text = format_appraisal({'state': 'complete', 'request_id': 'fixed-native-report', 'result': result})
    assert result['assessment']['contract'] is not None, result['assessment']['price_gaps']
    assert name in text
    assert line in text
    assert 'Trade tier:' in text
    if line.startswith('Throw Damage:'):
        assert 'Replenishes quantity' in text
