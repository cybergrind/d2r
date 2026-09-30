from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_reconciled_rare_trap_resistance_amulet_requires_same_item_combination():
    bundle = build()
    rid = 'fire-blast-starter-rare-amulet'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    keys = ['188:48', '39:0', '41:0', '43:0', '45:0']
    item = replace(facts('Amulet', 'rare'), stats={k: {'status': 'decoded', 'value': 1} for k in keys})
    ctx = {'player_class': 'Assassin'}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == set(keys)
    assert evaluate().annotations['188:48']['desirability'] == 'desirable'
    assert evaluate().annotations['39:0']['desirability'] == 'supporting'
    wrong_tree = replace(item, stats={('188:50' if k == '188:48' else k): v for k, v in item.stats.items()})
    assert not evaluate(wrong_tree).annotations
    mf = replace(item, stats={**item.stats, '80:0': {'status': 'decoded', 'value': 1}})
    assert evaluate(mf).annotations['80:0']['desirability'] == 'supporting'
    for key in keys:
        missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert not evaluate(missing, {**ctx, 'player_equipment': {'ring_left': item}}).annotations
    for change in ({'rarity': 'magic'}, {'rarity': 'crafted'}, {'identified': None}, {'ethereal': True}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={'player_class': 'Sorceress'}).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
    assert role['source']['corroborating'][0]['path'].endswith('e113x0l4.json')
