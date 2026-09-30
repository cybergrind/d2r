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
        (
            'Wizardspike',
            'Bone Knife',
            6,
            {'105:0': 50, '39:0': 75, '41:0': 75, '43:0': 75, '45:0': 75, '217:0': 2, '77:0': 15, '27:0': 15},
        ),
        (
            'Suicide Branch',
            'Burnt Wand',
            2,
            {'127:0': 1, '105:0': 50, '77:0': 10, '7:0': 40, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10},
        ),
        ('Spectral Shard', 'Blade', 2, {'105:0': 50, '9:0': 50, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10}),
        (
            'The Oculus',
            'Swirling Crystal',
            4,
            {
                '83:1': 3,
                '105:0': 30,
                '80:0': 50,
                '39:0': 20,
                '41:0': 20,
                '43:0': 20,
                '45:0': 20,
                '3:0': 20,
                '1:0': 20,
                '138:0': 5,
            },
        ),
        ("Death's Fathom", 'Dimensional Shard', 2, {'83:1': 3, '331:0': 15, '105:0': 20, '39:0': 25, '41:0': 25}),
        ("Eschuta's Temper", 'Eldritch Orb', 2, {'83:1': 1, '105:0': 40, '1:0': 20, '329:0': 10}),
    ],
)
def test_caster_weapon_modes_and_ethereal_casting(name, base, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-weapon-gear')]
    assert len(roles) == count
    excluded = {'19:0': 100, '50:0': 10, '51:0': 100, '330:0': 20, '198:4229': 2}
    item = replace(
        facts(base, 'unique', name),
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, **excluded}.items()},
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate, player=klass, configs=configs, role=role):
            ctx = {'player_class': player}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == set(values)
        eth = evaluate(replace(item, ethereal=True))
        assert set(eth.annotations) == (set() if name == 'Wizardspike' else set(values))
        for patch in ({'rarity': 'rare'}, {'sockets': 2}, {'base_code': facts('Jewel').base_code}):
            assert not evaluate(replace(item, **patch)).annotations
        assert not evaluate(item, 'Barbarian').annotations
        if name == "Death's Fathom":
            assert 'Blizzard' not in ' '.join(role['conditions'])
