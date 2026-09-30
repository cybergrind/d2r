from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'values'),
    [
        ('Magefist', 'Light Gauntlets', 16, {'105:0': 20, '27:0': 25}),
        ('Peasant Crown', 'War Hat', 9, {'127:0': 1, '96:0': 15, '3:0': 20, '1:0': 20, '74:0': 6}),
        ('Tarnhelm', 'Skull Cap', 12, {'127:0': 1, '80:0': 25}),
        (
            'Suicide Branch',
            'Burnt Wand',
            8,
            {'127:0': 1, '105:0': 50, '77:0': 10, '7:0': 40, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10},
        ),
        ('Silkweave', 'Mesh Boots', 7, {'96:0': 30, '77:0': 10, '138:0': 5, '32:0': 200}),
        ('Goldskin', 'Full Plate Mail', 1, {'79:0': 100, '39:0': 35, '41:0': 35, '43:0': 35, '45:0': 35}),
    ],
)
def test_caster_and_progression_utilities_use_only_build_relevant_properties(name, base, count, values):
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r.get('names') == [name] and r['id'].endswith('-caster-progression-alternative')
    ]
    assert len(roles) == count
    for role in roles:
        expected = set(values)
        if name == 'Magefist' and role['build'] in (
            'enchant-sorceress',
            'fire-blast-assassin',
            'fire-warlock-guide',
            'fissure-druid',
            'meteor-sorceress',
            'wake-of-fire-assassin',
        ):
            expected.add('126:1')
        item = replace(
            facts(base, 'unique', name),
            stats={
                k: {'status': 'decoded', 'value': v}
                for k, v in {'126:1': 1, '48:0': 1, '49:0': 6, '79:0': 75, '16:0': 150, **values}.items()
            },
        )
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, configs=configs, context=context, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == expected
        assert not evaluate(replace(item, rarity='rare')).annotations
        if name == 'Suicide Branch':
            assert set(evaluate(replace(item, ethereal=True)).annotations) == expected
        else:
            assert not evaluate(replace(item, ethereal=True)).annotations
