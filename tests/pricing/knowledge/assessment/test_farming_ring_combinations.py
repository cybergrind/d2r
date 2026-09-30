from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts
from tests.pricing.knowledge.assessment.test_farming_gear_priorities import PIECES


@pytest.mark.parametrize('magic', [False, True])
def test_farming_ring_combinations_are_quality_and_whole_item_specific(magic):
    bundle = build()
    rid = 'lightning-mf-magic-ring' if magic else 'meteor-mf-rare-ring'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = {'80:0': 5, '105:0': 10, '7:0': 10, '39:0': 5, '41:0': 5, '43:0': 5, '45:0': 5, '19:0': 100}
    item = replace(
        facts('Ring', 'magic' if magic else 'rare'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {
        'player_class': 'Sorceress',
        'player_total_fcr': 117 if magic else 105,
        'player_total_fhr': 60,
        'player_items': PIECES,
    }
    wanted = {'80:0'} if magic else set(values) - {'19:0'}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == wanted
    for key in ('80:0', '105:0'):
        result = evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key}))
        assert set(result.annotations) == (wanted if magic and key == '105:0' else set())
    assert not evaluate(replace(item, rarity='rare' if magic else 'magic')).annotations
    assert not evaluate(replace(item, identified=False)).annotations
    assert not evaluate(context={**ctx, 'player_total_fcr': None}).annotations
    for piece in PIECES:
        assert not evaluate(context={**ctx, 'player_items': [p for p in PIECES if p != piece]}).annotations
    if not magic:
        assert not evaluate(replace(item, stats={**item.stats, '105:0': {'status': 'decoded', 'value': 9}})).annotations
    assert all(a['roll_quality'] == 'unassessed' for a in evaluate().annotations.values())
