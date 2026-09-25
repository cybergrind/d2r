import json
from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_javelin_glove_annotations_require_skill_ias_pair_and_keep_boss_dependency():
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = [
        c
        for c in compile_stat_configurations(reviews, profiles, root=ROOT)
        if 'glov' in c.types and c.role_id.startswith('lightning-')
    ]
    assert len(configs) == 5

    def evaluate(values, quality='rare', **changes):
        item = replace(
            facts('Chain Gloves', quality),
            stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
            **changes,
        )
        return StatsEvaluator().evaluate(item, configs, role_outcomes=assess_role_results(item, profiles))

    values = {'188:2': 2, '93:0': 20, '2:0': 5, '39:0': 10, '80:0': 5}
    result = evaluate(values)
    assert result.annotations['188:2']['desirability'] == 'desirable'
    assert result.annotations['93:0']['desirability'] == 'desirable'
    assert result.annotations['39:0']['desirability'] == 'supporting'
    assert result.annotations['39:0']['roll_quality'] == 'unassessed'
    for key in ('188:2', '93:0'):
        assert not evaluate({**values, key: 0}).annotations
        assert not evaluate({k: v for k, v in values.items() if k != key}, capture_complete=False).annotations
    assert not evaluate(values, ethereal=True).annotations
    assert not evaluate(values, quality='crafted').annotations
    assert not evaluate(values, quality='magic').annotations
    magic = evaluate({'188:2': 3, '93:0': 20}, quality='magic')
    assert set(magic.annotations) == {'188:2', '93:0'}
    assert all(a['configuration_ids'] == ('lightning-fury-standard-gloves-stats',) for a in magic.annotations.values())
    assert (
        next(c for c in magic.configurations if c['role_id'] == 'lightning-strike-boss-gloves')['status']
        == 'conditional'
    )
