from copy import deepcopy

from inventory_tracking.appraisal.sections import leveling_lines


def use(classes, **changes):
    return {
        'tier': 'high',
        'side': 'player',
        'classes': classes,
        'archetypes': ['general'],
        'required_level': 20,
        'reason': 'Standalone movement speed; no companion set piece needed.',
        'conditions': [],
        **changes,
    }


def test_repeated_class_recommendations_keep_one_line_and_scoped_conditions():
    classes = ['amazon', 'assassin', 'barbarian', 'druid', 'necromancer', 'paladin', 'sorceress', 'warlock']
    uses = [use([klass]) for klass in classes]
    uses[2]['conditions'] = ['After level 31 respec.']
    uses[5]['conditions'] = ['After level 18 respec.']
    result = {'assessment': {'leveling': uses}}
    original = deepcopy(result)
    assert leveling_lines(result) == [
        'Leveling: high — player, all classes, general; equip level 20. '
        'Standalone movement speed; no companion set piece needed.',
        '  Needs (barbarian): After level 31 respec.',
        '  Needs (paladin): After level 18 respec.',
    ]
    assert result == original


def test_distinct_roles_levels_and_reasons_remain_separate():
    uses = [
        use(['barbarian']),
        use(['amazon'], side='mercenary'),
        use(['sorceress'], required_level=30),
        use(['druid'], reason='Exceptional skill bonus.'),
        use(['paladin'], tier='low'),
        use(['assassin'], generic=True),
    ]
    lines = leveling_lines({'assessment': {'leveling': uses}})
    assert len(lines) == 4
    assert 'mercenary, amazon' in lines[1]
    assert 'equip level 30' in lines[2]
    assert 'Exceptional skill bonus.' in lines[3]


def test_shared_requirement_is_rendered_once_without_losing_shortfalls():
    uses = [
        use([klass], conditions=['Use with companion piece.'], requirements_fit={'shortfalls': ['Need 10 Strength.']})
        for klass in ('barbarian', 'amazon')
    ]
    lines = leveling_lines({'assessment': {'leveling': uses}})
    assert lines[1:] == ['  Needs: Need 10 Strength.', '  Needs: Use with companion piece.']
