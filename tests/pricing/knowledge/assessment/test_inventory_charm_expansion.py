from dataclasses import replace

import pytest

from inventory_tracking.items.stat_constants import CLASS_NAMES
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'klass'),
    [
        ('blood-boil-warlock-guide', 'Warlock'),
        ('summoner-warlock-guide', 'Warlock'),
        ('fire-wall-sorceress-guide', 'Sorceress'),
        ('frozen-orb-meteor-sorceress', 'Sorceress'),
        ('frozen-orb-sorceress', 'Sorceress'),
        ('hydra-sorceress', 'Sorceress'),
        ('zeal-paladin', 'Paladin'),
    ],
)
def test_remaining_guide_charms_work_at_minimum_rolls_without_wrong_class_torch(slug, klass):
    bundle = build()
    names = {'Annihilus', 'Hellfire Torch', "Gheed's Fortune"}
    roles = [
        r
        for r in bundle['profiles']
        if r['build'] == slug and r['id'].endswith('-gear-inventory-charm') and set(r.get('names', [])) <= names
    ]
    assert len(roles) == 3
    assert {r['names'][0] for r in roles} == names
    class_id = CLASS_NAMES.index(klass)
    for role in roles:
        name = role['names'][0]
        values = {'0:0': 10, '1:0': 10, '2:0': 10, '3:0': 10, '39:0': 10, '41:0': 10, '43:0': 10, '45:0': 10}
        if name == 'Annihilus':
            values.update({'127:0': 1, '85:0': 5})
            base = 'Small Charm'
        elif name == 'Hellfire Torch':
            values[f'83:{class_id}'] = 3
            base = 'Large Charm'
        else:
            values = {'80:0': 20, '79:0': 80, '87:0': 10}
            base = 'Grand Charm'
        item = replace(
            facts(base, 'unique', name), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}
        )
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, player=klass, configs=configs, role=role):
            context = {'player_class': player}
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values)
        for patch in ({'rarity': 'magic'}, {'ethereal': True}, {'sockets': 1}, {'base_code': facts('Jewel').base_code}):
            assert not evaluate(replace(item, **patch)).annotations
        if name == 'Hellfire Torch':
            wrong_id = 3 if klass != 'Paladin' else 7
            wrong = {k: v for k, v in item.stats.items() if not k.startswith('83:')}
            wrong[f'83:{wrong_id}'] = {'status': 'decoded', 'value': 3}
            assert not evaluate(replace(item, stats=wrong)).annotations
            assert not evaluate(replace(item, stats={**item.stats, **wrong})).annotations
        assert not any(k.startswith(('198:', '204:')) for k in role['important_stats'])
