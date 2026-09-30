"""Insight source reviews preserve exact Echoing variants and mercenary needs."""

import pytest

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import ROOT, read


@pytest.mark.parametrize('variant', range(3))
def test_echoing_insight_source_is_bound_to_exact_bearer_and_recipe(variant):
    pid = f'echoing-{variant}-insight-merc'
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == pid)
    use = next(
        r for r in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if r['profile_id'] == pid
    )
    occurrence = next(
        r
        for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences']
        if r.get('source_id') == 'pricing/data/wp-a-builds.json'
        and r.get('source_locator') == f'/echoing-strike-warlock-guide/variants/{variant}/merc/Weapon/0'
    )
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == occurrence['id']
    ]
    assert len(matches) == 1
    review = matches[0]
    assert review['profile_id'] == pid
    assert review['required_predicates'] == role['must']['all']
    assert review['required_conditions'] == role['conditions']
    assert review['required_dependencies'] == [dep['when'] for dep in role.get('depends_on', [])]
    result = compile_table_equivalence({'schema_version': 1, 'rows': matches}, [occurrence], [role], [use], ROOT)
    assert result[0]['state'] == 'reviewed'
