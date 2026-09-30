from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_duress_budget_kicker_requires_completed_reviewed_base():
    bundle = build()
    rid = 'dragon-talon-budget-duress'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Dusk Shroud', name='Duress'),
        runeword='Duress',
        sockets=3,
        socket_contents='filled',
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('136:0', 15), ('39:0', 15), ('41:0', 15), ('43:0', 45), ('45:0', 15)]
        },
    )
    context = {'player_class': 'Assassin'}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    assert evaluate().annotations['136:0']['desirability'] == 'desirable'
    assert len(evaluate().annotations) == 5
    assert evaluate(replace(item, rarity='superior')).annotations
    for change in (
        {'base_code': facts('Archon Plate').base_code},
        {'runeword': None},
        {'socket_contents': 'empty'},
        {'sockets': None},
        {'sockets': 2},
        {'rarity': 'magic'},
        {'identified': None},
        {'ethereal': True},
    ):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(ctx={'player_class': 'Paladin'}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    outcome = assess_role_results(item, [role], context)[0]
    assert outcome.status == 'partial'
    assert any('90' in c for c in role['conditions'])
    demand = bundle['guide_demand']['summaries']['Duress']
    assert 'dragon-talon-assassin' in demand['builds']
    assert demand['distinct_builds'] == len(set(demand['builds']))
    assert demand['grade'] == 'Pending'
