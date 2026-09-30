"""Fissure's mercenary words retain their setup conditions and preferences."""

import pytest

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import ROOT, read


TARGETS = (
    ('fissure-merc-ubers-flickering-flame', '1c3f80a65741d815282ed5e5'),
    ('fissure-starter-merc-bulwark', 'dbe3a83d97c20b67b9dc5711'),
    ('fissure-starter-merc-treachery', 'e84946a393c8a205483919c5'),
)


@pytest.mark.parametrize(('pid', 'oid'), TARGETS)
def test_registered_fissure_word_preserves_companions_and_ethereal_preference(pid, oid):
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
    assert review['required_preferences'] == role['preferences']
    result = compile_table_equivalence({'schema_version': 1, 'rows': matches}, [occurrence], [role], [use], ROOT)
    assert result[0]['state'] == 'reviewed'
