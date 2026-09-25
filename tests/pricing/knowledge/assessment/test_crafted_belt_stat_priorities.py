import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_crafted_belts import CASES
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('role', 'values'), CASES[:-1])
def test_caster_belt_annotations_preserve_combinations_and_loadout_gates(role, values):
    profiles = build()['profiles']
    profile = next(p for p in profiles if p['id'] == role)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1

    def evaluate(values, context=None, **changes):
        item = replace(
            facts('Sharkskin Belt', 'crafted'),
            stats={f'{k}:0': {'status': 'decoded', 'value': v} for k, v in values.items()},
            **changes,
        )
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [profile], context)
        )

    context = {'player_total_fcr': 117}
    result = evaluate(values, context)
    assert set(result.annotations) == {f'{k}:0' for k in values}
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    assert result.configurations[0]['role']['status'] == 'partial'
    for key in values:
        assert not evaluate({**values, key: 0}, context).annotations
        assert not evaluate({k: v for k, v in values.items() if k != key}, context, capture_complete=False).annotations
    for rarity in ('magic', 'rare'):
        assert not evaluate(values, context, rarity=rarity).annotations
    for ethereal in (True, None):
        assert not evaluate(values, context, ethereal=ethereal).annotations
    if profile.get('depends_on'):
        threshold = profile['depends_on'][0]['when']['value']
        assert not evaluate(values).annotations
        assert not evaluate(values, {'player_total_fcr': threshold - 1}).annotations
        assert evaluate(values, {'player_total_fcr': threshold}).annotations
    if role.startswith(('echoing', 'fire')):
        for resistance in (41, 43, 45):
            alternative = {k: v for k, v in values.items() if k != 39} | {resistance: 10}
            assert set(evaluate(alternative, context).annotations) == {f'{k}:0' for k in alternative}
    if 7 in values:
        assert not evaluate({(6 if k == 7 else k): v for k, v in values.items()}, context).annotations
