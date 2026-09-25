import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('suffix', 'key', 'minimum'), [('stability', '99:0', 24), ('precision', '2:0', 10)])
def test_shroud_priorities_require_suffix_and_empty_four_socket_base(suffix, key, minimum):
    role = f'strafe-amazon-{suffix}-shroud-socket-base'
    klass, base = 'Amazon', 'Dusk Shroud'
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    profile = next(p for p in profiles if p['id'] == role)
    assert profile['important_stats'] == [key]
    item = replace(
        facts(base, 'magic'), sockets=4, socket_contents='empty', stats={key: {'status': 'decoded', 'value': minimum}}
    )

    def evaluate(item, context=None):
        context = {'player_class': klass} if context is None else context
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
        )

    item = replace(item, stats={**item.stats, '31:0': {'status': 'decoded', 'value': 467}})
    result = evaluate(item)
    assert set(result.annotations) == {key}
    assert result.annotations[key]['desirability'] == 'desirable'
    assert result.annotations[key]['roll_quality'] == 'unassessed'
    assert result.configurations[0]['role']['status'] == 'partial'
    assert not evaluate(replace(item, stats={key: {'status': 'decoded', 'value': minimum - 1}})).annotations
    assert not evaluate(replace(item, stats={}, capture_complete=False)).annotations
    for sockets in (0, 1, 2, 3, None):
        assert not evaluate(replace(item, sockets=sockets)).annotations
    for contents in ('filled', 'partial', None):
        assert not evaluate(replace(item, socket_contents=contents)).annotations
    other = facts('Mage Plate', 'magic')
    assert not evaluate(replace(item, base_code=other.base_code)).annotations
    for changes in ({'rarity': 'rare'}, {'ethereal': True}, {'ethereal': None}, {'identified': False}):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'player_class': 'Sorceress'}):
        assert not evaluate(item, context).annotations
    other_key = '2:0' if key == '99:0' else '99:0'
    assert not evaluate(replace(item, stats={other_key: {'status': 'decoded', 'value': 100}})).annotations
    if suffix == 'precision':
        perfect = replace(item, stats={key: {'status': 'decoded', 'value': 15}})
        assert evaluate(perfect).annotations[key]['roll_quality'] == 'unassessed'
