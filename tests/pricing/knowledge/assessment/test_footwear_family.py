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
        ("Aldur's Advance", 'Battle Boots', 'set', 19, {'96:0': 40, '7:0': 50, '39:0': 40}),
        ('Waterwalk', 'Sharkskin Boots', 'unique', 14, {'96:0': 20, '7:0': 45, '2:0': 15, '40:0': 5}),
        (
            'Sandstorm Trek',
            'Scarabshell Boots',
            'unique',
            17,
            {'96:0': 20, '99:0': 20, '0:0': 10, '3:0': 10, '45:0': 40},
        ),
    ],
)
def test_reviewed_boot_alternatives_keep_native_minimum_benefits(name, base, quality, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-boots-alternative')]
    assert len(roles) == count
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        item = replace(
            facts(base, quality, name),
            stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, '127:0': 3, '16:0': 200}.items()},
        )
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        result = StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [role], context)
        )
        assert set(result.annotations) == set(values)
    assert len(bundle['guide_demand']['summaries'][name]['alternative_builds']) >= count
