import pytest

from pricing.knowledge.assessment.maintenance.source_context_reviews import (
    branch_context_matches,
    occurrence_context_supported,
)


@pytest.mark.parametrize('slot', ['Charms', 'Unique Charms'])
def test_inventory_charm_context_requires_player_and_known_class(slot):
    occurrence = {'slot': slot, 'side': 'player', 'class': 'Paladin'}
    assert occurrence_context_supported('player_equipment', occurrence)
    assert not occurrence_context_supported('player_equipment', {**occurrence, 'side': 'merc'})
    assert not occurrence_context_supported('player_equipment', {**occurrence, 'class': None})


@pytest.mark.parametrize(
    ('role_slot', 'source_slot', 'expected'),
    [
        ('Charms', 'Unique Charms', True),
        ('Unique Charms', 'Charms', True),
        ('Charms', 'Weapon', False),
        ('Weapon', 'Unique Charms', False),
    ],
)
def test_charm_alias_preserves_inventory_slot_and_class(role_slot, source_slot, expected):
    role = {'slot': role_slot, 'must': {'op': 'context_eq', 'field': 'player_class', 'value': 'Paladin'}}
    occurrence = {'slot': source_slot, 'side': 'player', 'class': 'Paladin'}
    branch = {'player_class': 'Paladin', 'configuration_review': 'Reviewed active inventory charm use.'}
    assert branch_context_matches('player_equipment', branch, role, occurrence, 'Charm') is expected
    assert not branch_context_matches('player_equipment', branch, role, {**occurrence, 'class': 'Sorceress'}, 'Charm')
