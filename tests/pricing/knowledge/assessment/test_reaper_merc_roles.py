from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_reaper_merc_roles_require_a_compatible_bearer_and_actual_curse_units():
    b = build()
    roles = [
        r for r in b['profiles'] if r.get('names') == ["The Reaper's Toll"] and r['id'].endswith('-named-merc-weapon')
    ]
    assert len(roles) == 6
    values = {'17:0': 240, '18:0': 240, '198:5569': 33, '60:0': 15, '141:0': 33, '115:0': 1, '54:0': 4, '55:0': 44}
    item = replace(
        facts('Thresher', 'unique', "The Reaper's Toll"),
        ethereal=True,
        stats={
            k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k.startswith('198:') else {})}
            for k, v in values.items()
        },
    )
    for role in roles:
        configs = [
            configuration_from_row(c) for c in b['stat_evaluation']['configurations'] if c['role_id'] == role['id']
        ]
        context = {'player_class': role['must']['all'][0]['value'], 'mercenary_type': role['mercenary_type']}

        def evaluate(candidate, ctx=context, configs=configs, role=role):
            return StatsEvaluator().evaluate(
                candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
            )

        assert set(evaluate(item).annotations) == set(values)
        assert set(evaluate(replace(item, ethereal=False)).annotations) == set(values)
        assert not evaluate(item, {**context, 'mercenary_type': 'Act 1 Cold'}).annotations
        assert not evaluate(replace(item, base_code=facts('Partizan').base_code)).annotations
        assert not evaluate(replace(item, rarity='rare')).annotations
        wrong = replace(item, stats={**item.stats, '198:5569': {'status': 'decoded', 'value': 33, 'unit': 'level'}})
        assert '198:5569' not in evaluate(wrong).annotations
