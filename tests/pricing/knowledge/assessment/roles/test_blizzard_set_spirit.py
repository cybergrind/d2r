from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


PIECES = [
    "Tal Rasha's Lidless Eye",
    "Tal Rasha's Horadric Crest",
    "Tal Rasha's Guardianship",
    "Tal Rasha's Fine-Spun Cloth",
    "Tal Rasha's Adjudication",
]


def test_full_set_spirit_requires_five_player_pieces_and_both_real_loadout_totals():
    bundle = build()
    rid = 'blizzard-set-spirit-shield'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = {'127:0': 2, '105:0': 25, '99:0': 55, '9:0': 89, '3:0': 22, '41:0': 35, '43:0': 35, '45:0': 35}
    item = replace(
        facts('Monarch', name='Spirit'),
        runeword='Spirit',
        sockets=4,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': 'Sorceress', 'player_items': PIECES, 'player_total_fcr': 105, 'player_total_fhr': 86}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == set(values)
    for piece in PIECES:
        assert not evaluate(context={**ctx, 'player_items': [p for p in PIECES if p != piece]}).annotations
    for field, target in (('player_total_fcr', 105), ('player_total_fhr', 86)):
        for value in (None, True, str(target), target - 1):
            assert not evaluate(context={**ctx, field: value}).annotations
        assert set(evaluate(context={**ctx, field: target + 1}).annotations) == set(values)
    for context in (
        {'player_class': 'Sorceress', 'mercenary_items': PIECES, 'player_total_fcr': 105, 'player_total_fhr': 86},
        {**ctx, 'player_items': None},
        {**ctx, 'player_class': 'Paladin'},
    ):
        assert not evaluate(context=context).annotations
    for change in (
        {'name': 'Other'},
        {'base_code': facts('Targe').base_code},
        {'runeword': None},
        {'socket_contents': 'empty'},
        {'sockets': 3},
        {'rarity': 'magic'},
    ):
        assert not evaluate(replace(item, **change)).annotations
    # The same build's Starter and Set variants still contribute only one breadth vote.
    demand = bundle['guide_demand']['summaries']['Spirit']
    assert demand['distinct_builds'] >= 6
    assert demand['distinct_builds'] == len(set(demand['builds']))

    assert demand['builds'].count('blizzard-sorceress') == 1
