from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'class_name', 'values', 'irrelevant'),
    [
        ('Wormskull', 'Bone Helm', 'Necromancer', {'83:2': 1, '9:0': 10, '45:0': 25}, {'60:0': 5, '57:0': 102}),
        ('Twitchthroe', 'Studded Leather', 'Amazon', {'93:0': 20, '99:0': 20, '0:0': 10, '2:0': 10}, {'20:0': 25}),
        ('The Gnasher', 'Hand Axe', 'Paladin', {'135:0': 50, '136:0': 20, '0:0': 8}, {'17:0': 70, '18:0': 70}),
    ],
)
def test_specialist_gear_excludes_benefits_inapplicable_to_the_build(name, base, class_name, values, irrelevant):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-utility-alternative')]
    assert len(roles) == 1
    role = roles[0]
    item = replace(
        facts(base, 'unique', name),
        stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, **irrelevant}.items()},
    )
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
    ]

    def evaluate(candidate, cls=class_name):
        context = {'player_class': cls}
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate(item).annotations) == set(values)
    assert not evaluate(replace(item, ethereal=True)).annotations
    assert not evaluate(item, 'Sorceress').annotations
    assert not evaluate(replace(item, rarity='rare')).annotations
