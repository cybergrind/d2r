import json
from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_lancer_javelin_total_skills_and_exact_speed_remain_candidate_only():
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c
        for c in compile_stat_configurations(reviews, profiles, root=ROOT)
        if c.role_id == 'lightning-fury-starter-lancers-javelin'
    ]
    assert len(configs) == 1

    def evaluate(skills=4, speed=40, context=None, **changes):
        context = {'player_class': 'Amazon'} if context is None else context
        item = replace(
            facts('Matriarchal Javelin', 'magic'),
            stats={'188:2': {'status': 'decoded', 'value': skills}, '93:0': {'status': 'decoded', 'value': speed}},
            **changes,
        )
        return StatsEvaluator().evaluate(
            item, configs, context, role_outcomes=assess_role_results(item, profiles, context)
        )

    for skills in (4, 5, 6):
        result = evaluate(skills)
        assert set(result.annotations) == {'188:2', '93:0'}
        assert all(
            a['desirability'] == 'desirable' and a['roll_quality'] == 'unassessed' for a in result.annotations.values()
        )
        role = result.configurations[0]['role']
        assert role['status'] == 'partial'
        assert any('52%' in c for c in role['missing'])
    for skills in (0, 3, 7, None):
        assert not evaluate(skills).annotations
    for speed in (0, 39, 41, None):
        assert not evaluate(speed=speed).annotations
    for changes in (
        {'rarity': 'rare'},
        {'ethereal': True},
        {'ethereal': None},
        {'base_code': None},
        {'base_code': facts('Maiden Javelin', 'magic').base_code},
        {'identified': False},
        {'gaps': ['Duplicate native stat 188:2.']},
    ):
        assert not evaluate(**changes).annotations
    for context in ({}, {'player_class': 'Barbarian'}):
        assert not evaluate(context=context).annotations
