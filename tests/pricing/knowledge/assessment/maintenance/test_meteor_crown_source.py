"""Two-jewel Crown use retains native minimums and the guide's preferred rolls."""

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import ROOT, read


PID = 'meteor-sorceress-4-crown-ages'
OID = '3a3d16ec535e733ced521a97'


def test_registered_crown_source_keeps_two_compound_jewels_and_roll_target():
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == PID)
    use = next(
        u for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if u['profile_id'] == PID
    )
    occurrence = next(o for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if o['id'] == OID)
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    review = matches[0]
    assert review['profile_id'] == PID
    assert review['required_predicates'] == role['must']['all']
    assert review['required_dependencies'] == [d['when'] for d in role['depends_on']]
    assert review['required_preferences'] == role['preferences']
    assert review['required_conditions'] == role['conditions']
    assert (
        compile_table_equivalence({'schema_version': 1, 'rows': matches}, [occurrence], [role], [use], ROOT)[0]['state']
        == 'reviewed'
    )
