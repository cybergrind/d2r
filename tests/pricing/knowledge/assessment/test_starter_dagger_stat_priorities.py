import json
from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('quality', ['magic', 'rare'])
def test_abyss_starter_skill_alternatives_do_not_recommend_unavailable_fcr(quality):
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c for c in compile_stat_configurations(reviews, profiles, root=ROOT) if c.role_id == 'abyss-starter-dagger'
    ]
    assert len(configs) == 1
    skills = ('127:0', '83:7', '188:58', '107:402', '107:399')

    def evaluate(values, **changes):
        item = replace(
            facts('Cinquedeas', quality),
            stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
            **changes,
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    for key in skills:
        result = evaluate({key: 1})
        assert set(result.annotations) == {key}
        assert result.annotations[key]['desirability'] == 'desirable'
        assert result.configurations[0]['role']['status'] == 'partial'
        result = evaluate({key: 1, '105:0': 10, '17:0': 100, '19:0': 200})
        assert set(result.annotations) == {key}
        assert all(v['roll_quality'] == 'unassessed' for v in result.annotations.values())
        assert not evaluate({key: 0, '105:0': 20}).annotations
        assert not evaluate({key: None}, capture_complete=False).annotations
    assert set(evaluate(dict.fromkeys(skills, 1)).annotations) == set(skills)
    for wrong in ('188:57', '83:1', '97:402', '107:388'):
        assert not evaluate({wrong: 3, '105:0': 20}).annotations
    assert not evaluate({}, capture_complete=False).annotations
    for changes in (
        {'identified': False},
        {'item_type': 'swor'},
        {'rarity': 'unique'},
        {'rarity': 'crafted'},
        {'gaps': ['Duplicate native stat 107:402.']},
    ):
        assert not evaluate({'107:402': 1}, **changes).annotations


def test_starter_dagger_scope_matches_native_weapon_crafting_and_affixes():
    profile = next(p for p in build()['profiles'] if p['id'] == 'abyss-starter-dagger')
    assert profile['qualities'] == ['magic', 'rare']
    assert '105:0' not in profile['important_stats']
    assert 'cubemain' in profile['review_notes']
    assert 'magicsuffix' in profile['review_notes']
