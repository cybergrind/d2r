from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_fire_blast_soj_requires_actual_crafted_amulet_and_phoenix_loadout():
    bundle = build()
    rid = 'fire-blast-standard-soj-phoenix'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    ring = replace(
        facts('Ring', 'unique', 'The Stone of Jordan'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in [('127:0', 1), ('9:0', 20), ('77:0', 25)]},
    )
    amulet = replace(facts('Amulet', 'crafted'), stats={'105:0': {'status': 'decoded', 'value': 15}})
    shield = replace(facts('Monarch'), runeword='Phoenix')
    ctx = {
        'player_class': 'Assassin',
        'player_total_fcr': 102,
        'player_equipment': {'amulet': amulet, 'off_hand': shield},
    }

    def evaluate(candidate=ring, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {'127:0', '9:0', '77:0'}
    for value in (10, None, '15', True):
        bad = replace(amulet, stats={'105:0': {'status': 'decoded', 'value': value}})
        assert not evaluate(context={**ctx, 'player_equipment': {'amulet': bad, 'off_hand': shield}}).annotations
    for equipment in (
        {},
        {'amulet': None, 'off_hand': shield},
        {'amulet': replace(amulet, rarity='rare'), 'off_hand': shield},
        {'amulet': replace(amulet, identified=False), 'off_hand': shield},
        {'amulet': amulet},
        {'amulet': amulet, 'off_hand': replace(shield, runeword='Spirit')},
    ):
        assert not evaluate(context={**ctx, 'player_equipment': equipment}).annotations
    assert not evaluate(context={**ctx, 'player_total_fcr': 101}).annotations
    assert not evaluate(
        context={
            **ctx,
            'player_equipment': None,
            'player_items': ['Phoenix', 'Crafted Caster Amulet'],
            'player_total_fcr': 200,
        }
    ).annotations
    assert not evaluate(replace(ring, identified=False)).annotations
    assert not evaluate(replace(ring, ethereal=True)).annotations
    assert bundle['guide_demand']['summaries']['The Stone of Jordan']['distinct_builds'] >= 9
    assert bundle['guide_demand']['summaries']['The Stone of Jordan']['distinct_builds'] == len(
        set(bundle['guide_demand']['summaries']['The Stone of Jordan']['builds'])
    )
