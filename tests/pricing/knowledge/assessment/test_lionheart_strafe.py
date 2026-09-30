from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_strafe_lionheart_player_attributes_are_distinct_from_mercenary_benefits():
    bundle = build()
    rid = 'strafe-amazon-0-player-lionheart'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    values = {
        '17:0': 20,
        '18:0': 20,
        '7:0': 50,
        '0:0': 25,
        '2:0': 15,
        '3:0': 20,
        '39:0': 30,
        '41:0': 30,
        '43:0': 30,
        '45:0': 30,
    }
    item = replace(
        facts('Mage Plate', name='Lionheart'),
        runeword='Lionheart',
        sockets=3,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    context = {'player_class': 'Amazon'}

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate(item).annotations) == set(values)
    assert evaluate(item).annotations['3:0']['desirability'] == 'supporting'
    for changes in (
        {'ethereal': True},
        {'runeword': None},
        {'sockets': 2},
        {'socket_contents': 'empty'},
        {'rarity': 'magic'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
