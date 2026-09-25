import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('kind', ['crafted', 'cruel'])
@pytest.mark.parametrize('slot', ['weapon', 'offhand'])
def test_throwing_priorities_require_source_quality_base_combination_and_no_cold(kind, slot):
    profiles = build()['profiles']
    role = f'double-throw-starter-{kind}-{slot}'
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    quality, base = ('crafted', 'Balanced Axe') if kind == 'crafted' else ('magic', 'Winged Axe')
    values = {'17:0': 201, '18:0': 201}
    if kind == 'crafted':
        values = {'83:4': 1, '93:0': 10, '17:0': 80, '18:0': 80, '60:0': 4, '7:0': 20}

    def evaluate(values, context=None, **changes):
        context = {'player_class': 'Barbarian'} if context is None else context
        item = replace(
            facts(base, quality), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
        )
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
        )

    result = evaluate(values)
    assert set(result.annotations) == set(values)
    assert all(
        a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
    )
    assert result.configurations[0]['role']['status'] == 'partial'
    for key in values:
        assert not evaluate({**values, key: 0}).annotations
        assert not evaluate({k: v for k, v in values.items() if k != key}, capture_complete=False).annotations
    for cold in ('54:0', '55:0'):
        assert not evaluate({**values, cold: 1}).annotations
    assert not evaluate(values, capture_complete=False).annotations
    for changes in (
        {'rarity': 'rare'},
        {'ethereal': True},
        {'ethereal': None},
        {'identified': False},
        {'base_code': None},
    ):
        assert not evaluate(values, **changes).annotations
    for context in ({}, {'player_class': 'Amazon'}):
        assert not evaluate(values, context).annotations
    if kind == 'cruel':
        for value in (200, 301):
            assert not evaluate({'17:0': value, '18:0': value}).annotations
        assert evaluate({'17:0': 300, '18:0': 300}).annotations
        assert evaluate({**values, '93:0': 10}).annotations['93:0']['desirability'] == 'supporting'
    else:
        assert not evaluate({('6:0' if k == '7:0' else k): v for k, v in values.items()}).annotations
