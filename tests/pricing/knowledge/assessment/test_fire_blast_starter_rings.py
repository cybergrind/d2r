from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('quality', ['magic', 'rare'])
def test_starter_resistance_rings_keep_quality_and_mana_kill_distinctions(quality):
    bundle = build()
    rid = f'fire-blast-starter-{quality}-resistance-ring'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    stats = {'43:0': {'status': 'decoded', 'value': 1}}
    if quality == 'rare':
        stats['138:0'] = {'status': 'decoded', 'value': 1}
    item = replace(facts('Ring', quality), stats=stats)
    ctx = {'player_class': 'Assassin'}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == set(stats)
    for key in stats:
        missing = replace(item, stats={k: v for k, v in stats.items() if k != key})
        assert not evaluate(missing, {**ctx, 'player_equipment': {'ring_left': item}}).annotations
    for change in (
        {'rarity': 'rare' if quality == 'magic' else 'magic'},
        {'rarity': 'crafted'},
        {'identified': None},
        {'ethereal': True},
    ):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    if quality == 'rare':
        mf = replace(item, stats={**stats, '80:0': {'status': 'decoded', 'value': 1}})
        assert evaluate(mf).annotations['80:0']['desirability'] == 'supporting'
        regen = replace(item, stats={'43:0': stats['43:0'], '27:0': {'status': 'decoded', 'value': 25}})
        assert not evaluate(regen).annotations
        assert any('credited kills' in c for c in role['conditions'])
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
    assert role['source']['corroborating'][0]['path'].endswith('e113x0l4.json')
