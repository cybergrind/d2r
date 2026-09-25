import json
from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import ROOT, build
from pricing.knowledge.assessment.maintenance.stat_configurations import compile_stat_configurations
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_ring_markers_require_complete_role_combination_and_preserve_unresolved_uses():
    profiles = build()['profiles']
    reviews = json.loads((ROOT / 'pricing/knowledge/assessment/rules/stat_use_reviews.json').read_text())['reviews']
    configs = compile_stat_configurations(reviews, profiles, root=ROOT)
    ring_configs = [c for c in configs if 'ring' in c.types]
    assert len(ring_configs) == 6

    def assess(values, **changes):
        item = replace(
            facts('Ring', 'rare'), stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()}, **changes
        )
        return StatsEvaluator().evaluate(item, ring_configs, role_outcomes=assess_role_results(item, profiles))

    values = {'105:0': 10, '9:0': 20, '39:0': 5, '43:0': 10}
    result = assess(values)
    assert result.annotations['105:0']['desirability'] == 'desirable'
    assert result.annotations['9:0']['desirability'] == 'supporting'
    assert result.annotations['39:0']['desirability'] == 'supporting'
    assert result.annotations['9:0']['roll_quality'] == 'unassessed'
    assert not assess({**values, '39:0': 0}).annotations
    assert not assess({k: v for k, v in values.items() if k != '39:0'}, capture_complete=False).annotations
    assert not assess(values, rarity='magic').annotations
    # Separate MF configuration may independently justify FCR, but not the missing Starter combination.
    independent = assess({'105:0': 10, '80:0': 5})
    assert independent.annotations['105:0']['configuration_ids'] == (
        'blizzard-mf-ring-stats',
        'blizzard-set-ring-stats',
    )
    assert independent.annotations['80:0']['desirability'] == 'supporting'
    tri = assess({'105:0': 10, '39:0': 10, '41:0': 10, '43:0': 10})
    assert not tri.annotations
    assert next(c for c in tri.configurations if c['role_id'] == 'nova-starter-ring')['status'] == 'conditional'
    assert next(c for c in tri.configurations if c['role_id'] == 'lightning-ubers-ring')['status'] == 'conditional'
    starter = assess({'0:0': 5, '7:0': 10, '43:0': 10})
    assert set(starter.annotations) == {'0:0', '7:0', '43:0'}
    assert all(a['desirability'] == 'supporting' for a in starter.annotations.values())
