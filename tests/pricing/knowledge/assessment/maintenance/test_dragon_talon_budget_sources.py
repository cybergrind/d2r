"""Budget kicker links preserve melee durability and elite boot preparation."""

import pytest

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import ROOT, read


TARGETS = (
    ('dragon-talon-budget-duress', '4d02d63cc2a1f75d766f9149'),
    ('dragon-talon-budget-goblin-toe', '799b236574cb35ae3e01c850'),
)


@pytest.mark.parametrize(('pid', 'oid'), TARGETS)
def test_budget_kicker_source_requires_reviewed_base_and_setup(pid, oid):
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
    assert review['required_dependencies'] == [dep['when'] for dep in role.get('depends_on', [])]
    result = compile_table_equivalence({'schema_version': 1, 'rows': matches}, [occurrence], [role], [use], ROOT)
    assert result[0]['state'] == 'reviewed'
