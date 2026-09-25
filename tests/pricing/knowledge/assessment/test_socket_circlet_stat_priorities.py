import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'klass', 'base', 'key', 'minimum'),
    [
        ('double-throw-barbarian-guide-speed-diadem-socket-base', 'Barbarian', 'Diadem', '96:0', 30),
        ('double-throw-barbarian-guide-nirvana-diadem-socket-base', 'Barbarian', 'Diadem', '2:0', 21),
        ('double-throw-barbarian-guide-luck-diadem-socket-base', 'Barbarian', 'Diadem', '80:0', 26),
        ('strafe-amazon-nirvana-diadem-socket-base', 'Amazon', 'Diadem', '2:0', 21),
        ('strafe-amazon-speed-diadem-socket-base', 'Amazon', 'Diadem', '96:0', 30),
        ('berserk-barbarian-luck-tiara-socket-base', 'Barbarian', 'Tiara', '80:0', 26),
    ],
)
def test_socket_circlet_markers_require_empty_three_socket_base(role, klass, base, key, minimum):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    item = replace(
        facts(base, 'magic'), sockets=3, socket_contents='empty', stats={key: {'status': 'decoded', 'value': minimum}}
    )

    def evaluate(item, context=None):
        context = {'player_class': klass} if context is None else context
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
        )

    result = evaluate(item)
    assert set(result.annotations) == {key}
    assert result.annotations[key]['desirability'] == 'desirable'
    assert result.annotations[key]['roll_quality'] == 'unassessed'
    assert result.configurations[0]['role']['status'] == 'partial'
    assert not evaluate(replace(item, stats={key: {'status': 'decoded', 'value': minimum - 1}})).annotations
    assert not evaluate(replace(item, stats={}, capture_complete=False)).annotations
    for sockets in (0, 1, 2, None):
        assert not evaluate(replace(item, sockets=sockets)).annotations
    for contents in ('filled', 'partial', None):
        assert not evaluate(replace(item, socket_contents=contents)).annotations
    other = facts('Tiara' if base == 'Diadem' else 'Diadem', 'magic')
    assert not evaluate(replace(item, base_code=other.base_code)).annotations
    for changes in ({'rarity': 'rare'}, {'ethereal': True}, {'ethereal': None}, {'identified': False}):
        assert not evaluate(replace(item, **changes)).annotations
    for context in ({}, {'player_class': 'Sorceress'}):
        assert not evaluate(item, context).annotations
