"""Named defensive/damage alternatives preserve exact variant qualifications."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read, validate


SPECS = (
    ('lightning-fury-amazon-guide-3-stormshield', 'ca6a88b825b2243485ce46b8', 'Stormshield'),
    ('lightning-sentry-assassin-2-griffon-eye', '610daa1df10d2cd5a653cc7b', "Griffon's Eye"),
)


def records(pid, oid, name):
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == pid)
    use = next(
        r for r in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if r['profile_id'] == pid
    )
    occurrence = next(r for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if r['id'] == oid)
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': oid,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': pid,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': name,
        'review_date': '2026-09-29',
        'reason': (
            'Explicit variant prose recommends this named alternative. Preserve class, native base, '
            'nonethereal and identification requirements and all use qualifications. No socket payload '
            'is prescribed, and the item does not establish the full offensive or defensive setup.'
        ),
        'required_predicates': deepcopy(role['must']['all']),
        'required_conditions': deepcopy(role['conditions']),
        'required_dependencies': [deepcopy(dep['when']) for dep in role.get('depends_on', [])],
    }
    return review, occurrence, role, use


@pytest.mark.parametrize(('pid', 'oid', 'name'), SPECS)
def test_registered_prose_alternative_retains_qualifications(pid, oid, name):
    _, occurrence, role, use = records(pid, oid, name)
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == oid
    ]
    assert len(matches) == 1
    assert matches[0]['required_conditions'] == role['conditions']
    assert matches[0]['required_predicates'] == role['must']['all']
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
