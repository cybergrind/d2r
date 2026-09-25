import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_charge_stat_targets import charged
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('role', 'klass', 'gear'),
    [
        ('blizzard-sorceress-starter-charges-91', 'Sorceress', []),
        ('lightning-fury-amazon-guide-starter-charges-91', 'Amazon', []),
        ('fissure-druid-starter-charges-91', 'Druid', []),
        ('fissure-druid-ubers-charges-91', 'Druid', []),
        ('lightning-strike-amazon-starter-charges-91', 'Amazon', []),
        ('lightning-strike-amazon-ubers-charges-91', 'Amazon', ['Plague']),
        ('fire-warlock-guide-starter-charges-91', 'Warlock', []),
        ('lightning-sorceress-starter-charges-91', 'Sorceress', []),
        ('lightning-sorceress-ubers-charges-91', 'Sorceress', ['Infinity']),
    ],
)
def test_lower_resist_markers_preserve_opposite_infinity_requirements(role, klass, gear):
    profiles = build()['profiles']
    profile = next(p for p in profiles if p['id'] == role)
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == role]
    assert len(configs) == 1
    context = {'player_class': klass, 'mercenary_items': gear}
    key = f'204:{91 * 64 + 2}'

    def evaluate(stats, context=context, **changes):
        item = replace(facts('Bone Wand', 'magic'), stats=stats, **changes)
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, [profile], context)
        )

    for quality in ('magic', 'rare'):
        for ethereal in (False, True, None):
            result = evaluate({key: charged(1)}, rarity=quality, ethereal=ethereal)
            assert set(result.annotations) == {key}
            assert result.annotations[key]['roll_quality'] == 'unassessed'
            role_result = result.configurations[0]['role']
            assert role_result['status'] == 'partial'
            assert any('Ethereal' in s for s in role_result['missing'])
            assert any('immunity' in s for s in role_result['missing'])
    for stats in ({key: charged(0)}, {}, {'204:5253': charged(1)}, {key: {**charged(1), 'value': 2}}):
        assert not evaluate(stats).annotations
    for context in ({}, {'player_class': 'Barbarian'}):
        assert not evaluate({key: charged(1)}, context).annotations
    for changes in (
        {'rarity': 'unique'},
        {'identified': False},
        {'item_type': 'staf'},
        {'gaps': [f'Duplicate native stat {key}.']},
    ):
        assert not evaluate({key: charged(1)}, **changes).annotations
    if role in ('blizzard-sorceress-starter-charges-91', 'lightning-sorceress-ubers-charges-91'):
        assert not evaluate({key: charged(1)}, {'player_class': klass}).annotations
        opposite = [] if gear else ['Infinity']
        assert not evaluate({key: charged(1)}, {'player_class': klass, 'mercenary_items': opposite}).annotations
    if role == 'lightning-sorceress-ubers-charges-91':
        assert any('Mephisto' in s for s in role_result['missing'])
