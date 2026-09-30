from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'quality', 'count', 'values'),
    [
        (
            'Spectral Shard',
            'Blade',
            'unique',
            5,
            {'105:0': 50, '9:0': 50, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10, '19:0': 55},
        ),
        ('Bloodfist', 'Heavy Gloves', 'unique', 5, {'7:0': 40, '99:0': 30, '93:0': 10, '21:0': 5}),
        (
            "Eschuta's Temper",
            'Eldritch Orb',
            'unique',
            3,
            {'83:1': 3, '105:0': 40, '1:0': 30, '329:0': 20, '330:0': 20},
        ),
        (
            "Immortal King's Detail",
            'War Belt',
            'set',
            3,
            {'0:0': 25, '39:0': 28, '41:0': 31, '31:0': 36, '99:0': 25, '36:0': 20},
        ),
    ],
)
def test_caster_survival_alternatives_only_prioritize_applicable_native_stats(name, base, quality, count, values):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-caster-survival-alternative')
    ]
    assert len(roles) == count
    item = replace(facts(base, quality, name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()})
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, role=role, context=context, configs=configs):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        if name == 'Spectral Shard':
            expected = set(values) - {'19:0'}
        elif name == 'Bloodfist':
            expected = {'7:0', '99:0'}
            if role['build'] in ('dream-paladin', 'smite-paladin'):
                expected.add('93:0')
            if role['build'] == 'dream-paladin':
                expected.add('21:0')
        elif name == "Eschuta's Temper":
            expected = {'83:1', '105:0', '1:0', '330:0' if role['build'] == 'lightning-sorceress' else '329:0'}
        else:
            expected = {'0:0', '39:0', '41:0', '31:0'}
        assert set(evaluate(item).annotations) == expected
        assert not evaluate(replace(item, base_code=facts('Cap').base_code)).annotations
        assert not evaluate(replace(item, sockets=2)).annotations
        eth = evaluate(replace(item, ethereal=True)).annotations
        assert set(eth) == (expected if name in ('Spectral Shard', "Eschuta's Temper") else set())
