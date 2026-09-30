from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


PIECES = ["Tal Rasha's Guardianship", "Tal Rasha's Fine-Spun Cloth", "Tal Rasha's Adjudication"]


@pytest.mark.parametrize('short', ['blizzard', 'meteor', 'lightning'])
@pytest.mark.parametrize('boots', [True, False])
def test_farming_gear_priorities_preserve_loadout_without_maximum_roll_minima(short, boots):
    bundle = build()
    rid = short + '-mf-' + ('war-traveler' if boots else 'chance-guards')
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = {'80:0': 30 if boots else 25, '16:0': 190, '19:0': 25, '79:0': 200}
    if boots:
        values.update({'96:0': 25, '0:0': 10, '3:0': 10})
    wanted = {'80:0', '96:0', '0:0', '3:0'} if boots else {'80:0'}
    item = replace(
        facts('Battle Boots' if boots else 'Chain Gloves', 'unique', 'War Traveler' if boots else 'Chance Guards'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {
        'player_class': 'Sorceress',
        'player_items': PIECES,
        'player_total_fcr': 117 if short == 'lightning' else 105,
        'player_total_fhr': 60,
    }

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == wanted
    for piece in PIECES:
        assert not evaluate(context={**ctx, 'player_items': [p for p in PIECES if p != piece]}).annotations
    assert not evaluate(context={**ctx, 'player_items': None, 'mercenary_items': PIECES}).annotations
    assert not evaluate(context={**ctx, 'player_total_fcr': ctx['player_total_fcr'] - 1}).annotations
    if short == 'meteor':
        assert not evaluate(context={**ctx, 'player_total_fhr': 59}).annotations
    for change in ({'name': 'Other'}, {'identified': False}, {'rarity': 'magic'}):
        assert not evaluate(replace(item, **change)).annotations
    for key in wanted:
        assert set(
            evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations
        ) == wanted - {key}
    if not boots:
        upgraded = replace(item, base_name='Vambraces', base_code=facts('Vambraces').base_code)
        assert set(evaluate(upgraded).annotations) == wanted
    summary = bundle['guide_demand']['summaries'][item.name]
    assert {'blizzard-sorceress', 'meteor-sorceress', 'lightning-sorceress'} <= set(summary['builds'])
    assert summary['distinct_builds'] == len(set(summary['builds']))
