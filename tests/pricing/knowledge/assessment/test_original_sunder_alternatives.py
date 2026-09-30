from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('name', 'count', 'key', 'penalty', 'value'),
    [
        ('Cold Rupture', 1, '187:0', '43:0', -90),
        ('Flame Rift', 6, '189:0', '39:0', -90),
        ('Crack of the Heavens', 4, '190:0', '41:0', -90),
        ('Rotting Fissure', 1, '191:0', '45:0', -90),
        ('Bone Break', 4, '192:0', '36:0', -20),
        ('Black Cleft', 1, '193:0', '37:0', -65),
    ],
)
def test_original_sunder_requires_native_immunity_and_keeps_negative_penalty_visible(name, count, key, penalty, value):
    bundle = build()
    roles = [
        r for r in bundle['profiles'] if r.get('names') == [name] and r['id'].endswith('-original-sunder-alternative')
    ]
    assert len(roles) == count
    item = replace(
        facts('Grand Charm', 'unique', name),
        stats={key: {'status': 'decoded', 'value': 300}, penalty: {'status': 'decoded', 'value': value}},
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

        assert set(evaluate(item).annotations) == {key, penalty}
        for change in ({'ethereal': True}, {'sockets': 1}, {'socket_contents': 'filled'}, {'name': 'Renewed ' + name}):
            assert not evaluate(replace(item, **change)).annotations
        missing = replace(item, stats={penalty: item.stats[penalty]})
        assert not evaluate(missing).annotations
        invalid = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': 301}})
        assert not evaluate(invalid).annotations
        unknown = replace(item, stats={key: item.stats[key], penalty: {'status': 'unresolved', 'value': value}})
        assert penalty not in evaluate(unknown).annotations
