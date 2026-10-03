import pytest

from pricing.knowledge.assessment.maintenance.stormshield_market_review import defense_review


def test_native_level_scaling_preserves_distinct_listing_conventions():
    assert defense_review({'1855': 148})['status'] == 'base_defense_compatible'
    result = defense_review({'1855': 517, '436': 371})
    assert result == {
        'status': 'displayed_total_convention',
        'possible_levels': [99],
        'candidate_base_defense': 146,
        'socket_contribution_verified': False,
    }
    # Even proven arithmetic does not prove empty sockets.
    assert not result['socket_contribution_verified']


@pytest.mark.parametrize('bonus', [True, -1, 0, 149, 151, 372, 3.75])
def test_bonus_must_be_an_integer_attainable_at_a_real_character_level(bonus):
    assert defense_review({'1855': 148, '436': bonus})['status'] == 'invalid_level_bonus'


def test_two_defense_fields_may_disagree_without_silently_preferring_one():
    assert defense_review({'1855': 148, '436': 150})['status'] == 'mixed_or_conflicting_defense_fields'
    assert defense_review({'1855': 519})['status'] == 'ambiguous_total_or_socket_contribution'
    assert defense_review({'436': 371})['status'] == 'missing_total_defense'
    assert defense_review({'399': 148})['status'] == 'missing_total_defense'


def test_conflicting_observation_ids_cannot_be_deduplicated_away():
    from pricing.knowledge.assessment.maintenance.stormshield_market_review import audit

    row = {'id': 'test', 'name': 'Stormshield', 'rarity': 'unique'}
    assert audit([row, row])['statuses'] == {'unverified_scope': 1}
    with pytest.raises(ValueError, match='Conflicting'):
        audit([row, {**row, 'properties': {'1855': 148}}])
