from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('name', ['Flickering Flame', 'Wisdom'])
def test_helmet_recipes_keep_projectile_stats_out_of_trap_priorities(name):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-helm-word-alternative')]
    assert len(roles) == 4
    values = (
        {'126:1': 3, '333:0': 15, '151:100': 8, '9:0': 75, '110:0': 50, '118:0': 1}
        if name == 'Flickering Flame'
        else {'153:0': 1, '138:0': 5, '1:0': 10, '156:0': 33, '62:0': 8, '119:0': 25}
    )
    item = replace(
        facts('Mask', 'normal', name),
        runeword=name,
        sockets=3,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, context=context, configs=configs):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        expected = set(values)
        if name == 'Wisdom' and role['build'] == 'wake-of-fire-assassin':
            expected -= {'156:0', '62:0', '119:0'}
        elif name == 'Wisdom' and role['build'] == 'lightning-fury-amazon-guide':
            expected.remove('119:0')
        assert set(evaluate(item).annotations) == expected
        for changes in (
            {'sockets': 2},
            {'socket_contents': 'empty'},
            {'ethereal': True},
            {'runeword': None},
            {'rarity': 'magic'},
        ):
            assert not evaluate(replace(item, **changes)).annotations
        pelt = replace(item, base_code=facts('Spirit Mask').base_code, item_type='pelt')
        assert bool(evaluate(pelt).annotations) is (context['player_class'] == 'Druid')
