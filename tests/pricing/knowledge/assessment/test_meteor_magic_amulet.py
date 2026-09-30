from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_meteor_volcanic_luck_amulet_accepts_low_roll_but_requires_loadout_breakpoints():
    bundle = build()
    rid = 'meteor-standard-volcanic-luck-amulet'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Amulet', 'magic'), stats={k: {'status': 'decoded', 'value': v} for k, v in [('188:8', 3), ('80:0', 26)]}
    )
    ctx = {'player_class': 'Sorceress', 'player_total_fcr': 63, 'player_total_fhr': 60}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert evaluate().annotations['188:8']['desirability'] == 'desirable'
    assert evaluate().annotations['80:0']['desirability'] == 'supporting'
    assert evaluate(context={**ctx, 'player_total_fcr': 105}).annotations
    for field, values in [('player_total_fcr', (62, None, '63', True)), ('player_total_fhr', (59, None, '60', True))]:
        for value in values:
            assert not evaluate(context={**ctx, field: value}).annotations
    for key, value in [('188:8', 2), ('80:0', 25)]:
        changed = replace(item, stats={**item.stats, key: {'status': 'decoded', 'value': value}})
        assert not evaluate(changed).annotations
    for change in ({'rarity': 'rare'}, {'identified': None}, {'ethereal': True}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={**ctx, 'player_class': 'Assassin'}).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
