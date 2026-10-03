from pathlib import Path

import pytest

from pricing.knowledge.definitions import build_definitions
from pricing.knowledge.range_audit import audit_ranges


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def named():
    return {(r['rarity'], r.get('table_id')): r for r in build_definitions(ROOT)['rows'] if r['rarity'] == 'set'}


def test_claws_unconditional_poison_skill_damage_is_a_fixed_native_property(named):
    claws = named['set', 88]
    assert claws['roll_ranges']['332'] == {
        'stat_id': 332,
        'min': 25,
        'max': 25,
        'property': 'extra-pois',
        'better': 'higher',
    }
    assert claws['game_definition']['aprop3a'] == 'extra-pois'
    assert 'prop5' not in claws['game_definition']


def test_civerb_unconditional_level_damage_is_a_coefficient_not_a_scalar_roll(named):
    cudgel = named['set', 2]
    assert cudgel['fixed_per_level_effects'] == [
        {'stat_id': 218, 'coefficient_raw': 8, 'denominator': 8},
    ]
    assert '218' not in cudgel['roll_ranges']
    assert cudgel['variable_per_level_effects'] == []
    assert cudgel['game_definition']['apar1a'] == 8


def test_pillar_count_based_bonuses_remain_outside_standalone_properties(named):
    pillar = named['set', 74]
    assert pillar['game_definition']['add func'] == 2
    assert pillar['roll_ranges']['31']['min'] == pillar['roll_ranges']['31']['max'] == 75
    assert '80' not in pillar['roll_ranges']
    assert not any(k.startswith('188') for k in pillar['roll_ranges'])


def test_range_audit_does_not_call_unconditional_extra_properties_set_bonuses():
    audit = audit_ranges(ROOT)
    rows = {(r['rarity'], r['table_id']): r for r in audit['items']}
    for table_id, slot in [(88, 'aprop3a'), (2, 'aprop1a')]:
        entry = next(p for p in rows['set', table_id]['properties'] if p['slot'] == slot)
        assert entry['status'] != 'conditional_set_bonus_review'
    claw = next(p for p in rows['set', 88]['properties'] if p['slot'] == 'aprop3a')
    assert claw['status'] == 'fixed_scalar'


@pytest.mark.parametrize('level', [1, 80, 99])
def test_civerb_native_coefficient_is_consumed_independently_of_character_level(level):
    from pricing.knowledge.assessment.adapters.capture import normalize
    from pricing.knowledge.assessment.mechanics.per_level import fixed_per_level_keys
    from pricing.knowledge.definition_store import catalog
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    item = Item('Grand Scepter', 'set', "Civerb's Cudgel", ((218, 0, 8),), viewer_level=level)
    definition = catalog().named['set', "Civerb's Cudgel"]
    assert fixed_per_level_keys(normalize(item.capture()), definition) == ({'218:0'}, [])
