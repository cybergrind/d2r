from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_goldfind_rune_swords import sword
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_gold_find_markers_require_exact_linked_payload_and_role_context():
    document = build()
    configs = [
        configuration_from_row(c)
        for c in document['stat_evaluation']['configurations']
        if c['role_id'].endswith('-lem-sword')
    ]
    assert len(configs) == 7

    def assess(item, context=None):
        context = {'player_class': 'Barbarian'} if context is None else context
        return StatsEvaluator().evaluate(
            item,
            configs,
            context,
            role_outcomes=assess_role_results(item, document['profiles'], context),
        )

    item = replace(sword(), stats={'79:0': {'status': 'decoded', 'value': 450}})
    result = assess(item)
    assert result.annotations['79:0']['desirability'] == 'desirable'
    assert len(result.annotations['79:0']['configuration_ids']) == 7
    assert all(c['role']['status'] == 'partial' for c in result.configurations)
    assert assess(replace(item, ethereal=True)).annotations == result.annotations
    for changed in (
        replace(item, socket_items=sword(['Lem Rune'] * 5 + ['Ist Rune']).socket_items),
        replace(item, socket_contents='unknown', filled_sockets=None, empty_sockets=None),
        replace(item, socket_items=[{**c, 'unit_id': 1} for c in item.socket_items]),
        replace(item, sockets=3),
        replace(item, base_code=facts('Broad Sword').base_code),
        replace(item, rarity='magic'),
        replace(item, identified=False),
        replace(item, stats={'79:0': {'status': 'decoded', 'value': 449}}),
        replace(facts('Crystal Sword'), stats=item.stats),
    ):
        assert not assess(changed).annotations
    assert not assess(item, {'player_class': 'Druid'}).annotations
    assert not assess(item, {}).annotations
