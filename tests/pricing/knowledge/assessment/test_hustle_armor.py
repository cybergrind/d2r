from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('side', 'count'), [('merc', 8), ('player', 2)])
def test_hustle_armor_uses_require_armor_recipe_and_wearer_durability(side, count):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r['id'].endswith('-hustle-armor-alternative') and r['side'] == side]
    assert len(roles) == count
    values = {'93:0': 40, '96:0': 65, '99:0': 20, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10}
    item = replace(
        facts('Mage Plate', 'normal', 'Hustle (armor)'),
        runeword='Hustle (armor)',
        ethereal=False,
        sockets=3,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, '97:29': 6}.items()},
    )
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, configs=configs, context=context):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values) | ({'97:29'} if side == 'player' else set())
        for quality in ('superior', 'low_quality'):
            assert set(evaluate(replace(item, rarity=quality)).annotations) == set(values) | (
                {'97:29'} if side == 'player' else set()
            )
        assert bool(evaluate(replace(item, ethereal=True)).annotations) is (side == 'merc')
        for changes in (
            {'runeword': 'Hustle (weapon)'},
            {'sockets': 2},
            {'socket_contents': 'empty'},
            {'rarity': 'magic'},
            {'base_code': facts('Quilted Armor').base_code},
        ):
            assert not evaluate(replace(item, **changes)).annotations
