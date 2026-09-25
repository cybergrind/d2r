from pricing.knowledge.assessment.mechanics.equipment import assess_requirements


def test_wearer_attributes_are_independent_and_unknown_is_not_zero():
    requirements = {'level': 20, 'strength': 100, 'dexterity': 50}
    context = {
        'player_level': 99,
        'player_strength': 200,
        'player_dexterity': 200,
        'mercenary_level': 20,
        'mercenary_strength': 90,
        'mercenary_dexterity': 50,
    }
    assert assess_requirements(requirements, 'player', context)['status'] == 'met'
    merc = assess_requirements(requirements, 'merc', context)
    assert merc['status'] == 'unmet'
    assert merc['shortfalls'] == ['Mercenary strength 90; requires 100.']
    assert assess_requirements(requirements, 'merc', {'player_level': 99})['status'] == 'unknown'
    assert assess_requirements({}, 'player', context)['status'] == 'unknown'
    assert assess_requirements({'level': 20}, 'player', context)['status'] == 'unknown'
    assert assess_requirements(requirements, 'player', {**context, 'player_strength': True})['status'] == 'unknown'
