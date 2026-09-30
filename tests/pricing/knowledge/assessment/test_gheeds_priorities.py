from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('gold', [False, True])
def test_gheeds_utility_has_distinct_farming_priorities_without_roll_minima(gold):
    bundle = build()
    rid = ('gold-find-barbarian-0' if gold else 'lightning-sorceress-0') + '-gheeds-inventory'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Grand Charm', 'unique', "Gheed's Fortune"),
        stats={
            k: {'status': 'decoded', 'value': v} for k, v in [('80:0', 20), ('79:0', 80), ('87:0', 10), ('127:0', 1)]
        },
    )

    def evaluate(candidate=item):
        return StatsEvaluator().evaluate(candidate, configs, role_outcomes=assess_role_results(candidate, [role]))

    result = evaluate()
    assert set(result.annotations) == {'80:0', '79:0', '87:0'}
    assert result.annotations['79:0']['desirability'] == ('desirable' if gold else 'supporting')
    for key in ('80:0', '79:0', '87:0'):
        assert set(evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations) == {
            '80:0',
            '79:0',
            '87:0',
        } - {key}
    for change in (
        {'name': 'Other'},
        {'rarity': 'magic'},
        {'identified': False},
        {'base_code': facts('Small Charm').base_code},
    ):
        assert not evaluate(replace(item, **change)).annotations
    uses = [p for p in bundle['profiles'] if p['id'].endswith('-gheeds-inventory')]
    assert len(uses) == 43
    assert not any('hardcore' in p['variant'].lower() for p in uses)
    assert not any(p['build'] == 'echoing-strike-warlock-guide' and p['variant'] == 'Ubers' for p in uses)
    assert bundle['guide_demand']['summaries']["Gheed's Fortune"]['distinct_builds'] >= 23
    assert bundle['guide_demand']['summaries']["Gheed's Fortune"]['distinct_builds'] == len(
        set(bundle['guide_demand']['summaries']["Gheed's Fortune"]['builds'])
    )
