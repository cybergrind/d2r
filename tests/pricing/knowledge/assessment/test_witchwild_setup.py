from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_witchwild_strafe_requires_upgraded_bow_and_two_distinct_jewels():
    bundle = build()
    roles = [r for r in bundle['profiles'] if r['id'] == 'strafe-amazon-witchwild-string-magic-find']
    assert len(roles) == 1
    values = {
        '17:0': 200,
        '18:0': 200,
        '250:0': 1,
        '198:4229': 2,
        '39:0': 40,
        '41:0': 40,
        '43:0': 40,
        '45:0': 40,
        '80:0': 25,
        '366:0': 10,
    }
    stats = {
        k: {'status': 'decoded', 'value': v, **({'unit': 'percent_chance'} if k == '198:4229' else {})}
        for k, v in values.items()
    }
    stone = {
        'name': "Protector's Stone",
        'item_type': 'cjwl',
        'unit_id': 1,
        'position': 0,
        'stats_complete': True,
        'stats': {'80:0': stats['80:0'], '366:0': stats['366:0']},
    }
    jewel = {'name': 'Jewel', 'item_type': 'jewl', 'unit_id': 2, 'position': 1, 'stats_complete': True, 'stats': {}}
    item = replace(
        facts('Diamond Bow', 'unique', 'Witchwild String'),
        stats={**stats, '157:0': {'status': 'decoded', 'value': 20}},
        sockets=2,
        socket_contents='filled',
        filled_sockets=2,
        empty_sockets=0,
        socket_items=[stone, jewel],
    )
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == roles[0]['id']
    ]
    context = {'player_class': 'Amazon'}

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, roles, context)
        )

    assert set(evaluate(item).annotations) == set(values)
    for patch in (
        {'base_code': facts('Short Siege Bow').base_code},
        {'ethereal': True},
        {'rarity': 'rare'},
        {'socket_items': [stone]},
        {'socket_items': [stone, {**jewel, 'item_type': 'rune'}]},
        {'socket_items': [stone, {**jewel, 'unit_id': 1}]},
        {'socket_items': [{**stone, 'name': "Guardian's Light"}, jewel]},
        {'socket_items': [{**stone, 'stats': {'80:0': {'status': 'decoded', 'value': 14}}}, jewel]},
    ):
        assert not evaluate(replace(item, **patch)).annotations
    wrong_unit = replace(item, stats={**item.stats, '198:4229': {'status': 'decoded', 'value': 2, 'unit': 'raw'}})
    assert '198:4229' not in evaluate(wrong_unit).annotations
    assert '157:0' not in roles[0]['important_stats']
