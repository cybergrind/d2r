from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_dracul_life_tap_is_separate_from_ordinary_leech_for_smite():
    bundle = build()
    roles = [
        r
        for r in bundle['profiles']
        if r.get('names') == ["Dracul's Grasp"] and r['id'].endswith('-dracul-alternative')
    ]
    assert len(roles) == 3
    values = {'198:5258': 5, '135:0': 25, '0:0': 15, '86:0': 10, '60:0': 10}
    item = replace(
        facts('Vampirebone Gloves', 'unique', "Dracul's Grasp"),
        stats={
            k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k.startswith('198:') else {})}
            for k, v in values.items()
        },
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

        expected = set(values) - ({'60:0'} if role['build'] == 'smite-paladin' else set())
        assert set(evaluate(item).annotations) == expected
        for change in ({'ethereal': True}, {'sockets': 1}, {'socket_contents': 'filled'}):
            assert not evaluate(replace(item, **change)).annotations
        untrusted = dict(item.stats)
        untrusted['198:5258'] = {'status': 'decoded', 'value': 5, 'unit': 'skill_level'}
        assert '198:5258' not in evaluate(replace(item, stats=untrusted)).annotations
