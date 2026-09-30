from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'base', 'count', 'values', 'irrelevant'),
    [
        (
            'Guardian Angel',
            'Templar Coat',
            17,
            {'40:0': 15, '42:0': 15, '44:0': 15, '46:0': 15},
            {'83:3': 1, '20:0': 20, '102:0': 30},
        ),
        (
            "The Gladiator's Bane",
            'Wire Fleece',
            14,
            {'34:0': 15, '35:0': 15, '153:0': 1, '99:0': 30, '110:0': 50},
            {'78:0': 20},
        ),
        ('Skin of the Flayed One', 'Demonhide Armor', 15, {'60:0': 5, '74:0': 15}, {'252:0': 10, '78:0': 15}),
        ('The Face of Horror', 'Mask', 15, {'0:0': 20, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10}, {'112:0': 64}),
    ],
)
def test_mercenary_unique_survival_alternatives_use_only_relevant_benefits(name, base, count, values, irrelevant):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-merc-native-alternative')]
    assert len(roles) == count
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        item = replace(
            facts(base, 'unique', name),
            ethereal=True,
            stats={k: {'status': 'decoded', 'value': v} for k, v in {**values, **irrelevant}.items()},
        )
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, configs=configs, context=context, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values)
        assert set(evaluate(replace(item, ethereal=False)).annotations) == set(values)
        assert not evaluate(replace(item, base_code=facts('Quilted Armor').base_code)).annotations
