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
        ("Aldur's Advance", 'Battle Boots', 6, {'96:0': 40, '7:0': 50, '39:0': 40}),
        ('Waterwalk', 'Sharkskin Boots', 6, {'96:0': 20, '7:0': 45, '2:0': 15, '40:0': 5}),
        ('Sandstorm Trek', 'Scarabshell Boots', 6, {'96:0': 20, '99:0': 20, '0:0': 10, '3:0': 10, '45:0': 40}),
        ('Silkweave', 'Mesh Boots', 2, {'96:0': 30, '77:0': 10, '32:0': 200, '138:0': 5}),
        ('Chance Guards', 'Chain Gloves', 6, {'80:0': 25}),
        ('Goldwrap', 'Heavy Belt', 6, {'80:0': 30}),
        ("Verdungo's Hearty Cord", 'Mithril Coil', 4, {'36:0': 10, '3:0': 30, '99:0': 10, '74:0': 10}),
        ("Bul-Kathos' Wedding Band", 'Ring', 6, {'127:0': 1, '216:0': 0.5}),
        ('Dwarf Star', 'Ring', 4, {'142:0': 15, '35:0': 12, '7:0': 40}),
        ('Peasant Crown', 'War Hat', 2, {'127:0': 1, '96:0': 15, '3:0': 20, '1:0': 20, '74:0': 6}),
    ],
)
def test_caster_accessories_preserve_low_rolls_and_damage_mode(name, base, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-accessory-gear')]
    assert len(roles) == count
    item = replace(
        facts(base, 'set' if name == "Aldur's Advance" else 'unique', name),
        stats={
            k: {'status': 'decoded', 'value': v} for k, v in {**values, '60:0': 10, '93:0': 10, '19:0': 100}.items()
        },
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

        expected = set(values)
        if name == 'Silkweave' and role['build'] == 'summoner-warlock-guide':
            expected.remove('138:0')
        assert set(evaluate(item).annotations) == expected
        assert not evaluate(replace(item, ethereal=True)).annotations
        if name == 'Sandstorm Trek':
            repairing = replace(item, ethereal=True, stats={**item.stats, '252:0': {'status': 'decoded', 'value': 20}})
            assert set(evaluate(repairing).annotations) == expected
        for patch in ({'rarity': 'rare'}, {'base_code': facts('Jewel').base_code}, {'sockets': 2}):
            assert not evaluate(replace(item, **patch)).annotations
        assert not evaluate(item, 'Barbarian').annotations
