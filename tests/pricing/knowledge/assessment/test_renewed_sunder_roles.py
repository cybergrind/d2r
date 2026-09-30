from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'count', 'immunity', 'penalty', 'penalty_value', 'pierce'),
    [
        ('Renewed Black Cleft', 9, '193:0', '37:0', -45, '358:0'),
        ('Renewed Bone Break', 3, '192:0', '36:0', -10, '366:0'),
        ('Renewed Cold Rupture', 2, '187:0', '43:0', -70, '335:0'),
        ('Renewed Crack of the Heavens', 11, '190:0', '41:0', -70, '334:0'),
        ('Renewed Flame Rift', 2, '189:0', '39:0', -70, '333:0'),
    ],
)
def test_renewed_identity_fixed_core_and_observed_rolls_are_separate_from_original(
    name, count, immunity, penalty, penalty_value, pierce
):
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-renewed-sunder')]
    assert len(roles) == count
    values = {immunity: 300, penalty: penalty_value, pierce: 10, '99:0': 12, '7:0': 65, '35:0': 5, '80:0': 25}
    item = replace(
        facts('Crafted Sunder Charm', 'unique', name),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    for role in roles:
        context = {'player_class': role['must']['all'][0]['value']}
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, context=context, configs=configs, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values)
        minimal = replace(item, stats={k: v for k, v in item.stats.items() if k in (immunity, penalty)})
        assert set(evaluate(minimal).annotations) == {immunity, penalty}
        unknown = replace(item, stats={**item.stats, pierce: {'status': 'unresolved', 'value': 10}})
        assert pierce not in evaluate(unknown).annotations
        wrong = replace(item, stats={**item.stats, immunity: {'status': 'decoded', 'value': 301}})
        assert not evaluate(wrong).annotations
        for patch in (
            {'base_code': facts('Grand Charm').base_code},
            {'name': name.removeprefix('Renewed ')},
            {'ethereal': True},
            {'sockets': 1},
            {'rarity': 'crafted'},
        ):
            assert not evaluate(replace(item, **patch)).annotations
        if role['build'] == 'echoing-strike-warlock-guide' and name == 'Renewed Black Cleft':
            assert any('Hex Purge' in c for c in role['conditions'])
        assert not any(k in role['important_stats'] for k in ('329:0', '330:0', '331:0', '357:0'))
