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
        ("Bul-Kathos' Wedding Band", 'Ring', 20, {'127:0': 1, '216:0': 45}),
        ("Skullder's Ire", 'Russet Armor', 19, {'127:0': 1, '240:0': 112, '35:0': 10}),
        (
            'Wizardspike',
            'Bone Knife',
            17,
            {'105:0': 50, '39:0': 75, '41:0': 75, '43:0': 75, '45:0': 75, '217:0': 180, '77:0': 15, '27:0': 15},
        ),
    ],
)
def test_explicit_named_utility_slots_highlight_only_the_reviewed_benefits(name, base, count, values):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-utility-alternative')]
    assert len(roles) == count
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        item = replace(
            facts(base, 'unique', name),
            stats={
                k: {'status': 'decoded', 'value': v} for k, v in {**values, '60:0': 5, '93:0': 40, '16:0': 200}.items()
            },
        )
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        result = StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [role], context)
        )
        assert set(result.annotations) == set(values)
        assert role['source']['quotes'] == [name]
