from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_deathbit_guide_upgrade_and_replenishment_are_required_for_both_hands():
    bundle = build()
    roles = [r for r in bundle['profiles'] if r.get('names') == ['Deathbit']]
    assert len(roles) == 2
    values = {'17:0': 180, '18:0': 180, '19:0': 450, '141:0': 40, '60:0': 9, '62:0': 6, '253:0': 25}
    item = replace(
        facts('Flying Knife', 'unique', 'Deathbit'),
        ethereal=True,
        stats={
            k: {'status': 'decoded', 'value': v, **({'unit': 'replenishment_rate'} if k == '253:0' else {})}
            for k, v in values.items()
        },
    )
    context = {'player_class': 'Barbarian'}
    for role in roles:
        configs = [
            configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]

        def evaluate(candidate, configs=configs, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
            )

        assert set(evaluate(item).annotations) == set(values)
        assert not evaluate(replace(item, base_code=facts('Battle Dart').base_code)).annotations
        assert not evaluate(
            replace(item, stats={**item.stats, '253:0': {'status': 'decoded', 'value': 25, 'unit': 'seconds'}})
        ).annotations
        assert not evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != '253:0'})).annotations
