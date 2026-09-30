"""The three pre-fight caster components retain exact bearer and facet evidence."""

import pytest

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import ROOT, read


TARGETS = (
    ('dragon-talon-budget-hexfire-merc', 'fc07982fce425f82dbb15311'),
    ('dragon-talon-budget-ormus-merc', '5e2b58109e0d34eeab437b42'),
    ('dragon-talon-budget-lidless-merc', '213c6a8301f2ab43696366d7'),
)


@pytest.mark.parametrize(('pid', 'oid'), TARGETS)
def test_prefight_mercenary_source_keeps_facet_and_wearer_requirements(pid, oid):
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == pid)
    use = next(
        r for r in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if r['profile_id'] == pid
    )
    occurrence = next(r for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if r['id'] == oid)
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == oid
    ]
    assert len(matches) == 1
    review = matches[0]
    assert review['profile_id'] == pid
    assert review['required_predicates'] == role['must']['all']
    assert review['required_conditions'] == role['conditions']
    assert review['required_dependencies'] == [dep['when'] for dep in role['depends_on']]
    assert review['required_preferences'] == role['preferences']
    result = compile_table_equivalence({'schema_version': 1, 'rows': matches}, [occurrence], [role], [use], ROOT)
    assert result[0]['state'] == 'reviewed'
