from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'sockets', 'values'),
    [
        (
            'Crown of Ages',
            'Corona',
            6,
            1,
            {
                '127:0': 1,
                '99:0': 30,
                '39:0': 20,
                '41:0': 20,
                '43:0': 20,
                '45:0': 20,
                '36:0': 10,
                '31:0': 349,
                '16:0': 50,
            },
        ),
        (
            'Stormshield',
            'Monarch',
            4,
            0,
            {'36:0': 35, '0:0': 30, '102:0': 35, '41:0': 25, '20:0': 25, '43:0': 60, '214:0': 3.75},
        ),
        ("Nightwing's Veil", 'Spired Helm', 1, 0, {'127:0': 2, '331:0': 8, '2:0': 10, '149:0': 5, '118:0': 1}),
    ],
)
def test_caster_defense_items_keep_native_rolls_sockets_and_element(name, base, count, sockets, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-defense-gear')]
    assert len(roles) == count
    item = replace(
        facts(base, 'unique', name),
        sockets=sockets,
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in {**values, '93:0': 20, '329:0': 15, '330:0': 15, '153:0': 1}.items()
        },
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        klass = role['must']['all'][0]['value']

        def evaluate(candidate, player=klass, role=role, configs=configs):
            ctx = {'player_class': player}
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == set(values)
        assert not evaluate(replace(item, ethereal=True)).annotations
        for patch in ({'rarity': 'rare'}, {'sockets': 3}, {'base_code': facts('Jewel').base_code}):
            assert not evaluate(replace(item, **patch)).annotations
        assert not evaluate(item, 'Barbarian').annotations
        if name == 'Crown of Ages':
            assert not evaluate(replace(item, sockets=0)).annotations
            assert set(evaluate(replace(item, sockets=2)).annotations) == set(values)
        if name == "Nightwing's Veil":
            assert 'Blizzard' not in ' '.join(role['conditions'])
