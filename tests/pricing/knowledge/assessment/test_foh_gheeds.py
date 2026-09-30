from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_foh_gheeds_minimum_farming_rolls_and_inventory_identity():
    bundle = build()
    rid = 'fist-of-the-heavens-paladin-gheeds-farming-charm'
    roles = [r for r in bundle['profiles'] if r['id'] == rid]
    assert len(roles) == 1
    configs = [configuration_from_row(r) for r in bundle['stat_evaluation']['configurations'] if r['role_id'] == rid]
    item = replace(
        facts('Grand Charm', 'unique', "Gheed's Fortune"),
        stats={
            k: {'status': 'decoded', 'value': v} for k, v in {'80:0': 20, '79:0': 80, '87:0': 10, '127:0': 2}.items()
        },
    )

    def evaluate(candidate, klass='Paladin'):
        ctx = {'player_class': klass}
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, roles, ctx)
        )

    assert set(evaluate(item).annotations) == {'80:0', '79:0', '87:0'}
    for patch in (
        {'name': 'Other'},
        {'base_code': facts('Small Charm').base_code},
        {'rarity': 'magic'},
        {'identified': False},
        {'ethereal': True},
        {'sockets': 1},
        {'socket_contents': 'filled'},
    ):
        assert not evaluate(replace(item, **patch)).annotations
    assert not evaluate(item, 'Sorceress').annotations
    demand = bundle['guide_demand']['summaries']["Gheed's Fortune"]
    assert demand['builds'].count('fist-of-the-heavens-paladin') == 1
