"""Warlock helmet source links retain socket payloads and Ubers companions."""

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read, validate
from tests.pricing.knowledge.assessment.maintenance.test_prose_named_alternatives import records as named_records


SPECS = (
    ('echoing-ubers-hellwarden-guardian-light', '476a9376d427b3cdae34454a', "Hellwarden's Will"),
    ('fire-warlock-guide-2-harlequin-defender-fire', '72575ac81a2e98fdfa76974f', 'Harlequin Crest'),
)


def records(pid, oid, name):
    result = named_records(pid, oid, name)
    result[0]['required_preferences'] = result[2].get('preferences', [])
    if pid.startswith('echoing'):
        result[0]['required_socket'] = {'required_socket_item': "Guardian's Light"}
    result[0]['reason'] = (
        'Exact variant helmet entry prescribes this named socketed jewel. Require the actual linked '
        'payload and native minimum modifiers. Preserve all player, base, identification and companion '
        'requirements; perfect rolls and full-build readiness are not inferred.'
    )
    return result


@pytest.mark.parametrize(('pid', 'oid', 'name'), SPECS)
def test_named_socketed_configuration_has_exact_source(pid, oid, name):
    assert validate(records(pid, oid, name))['state'] == 'reviewed'


@pytest.mark.parametrize(('pid', 'oid', 'name'), SPECS)
def test_verified_payload_cannot_be_removed(pid, oid, name):
    review, occurrence, role, use = records(pid, oid, name)
    role['must']['all'] = [p for p in role['must']['all'] if p.get('op') != 'socket_jewel_matches']
    use['profile_fingerprint'] = review['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='lost mandatory reviewed predicates'):
        validate((review, occurrence, role, use))


@pytest.mark.parametrize('companion', ['Sling', 'Renewed Black Cleft'])
def test_echoing_companions_remain_required(companion):
    review, occurrence, role, use = records(*SPECS[0])
    role['depends_on'] = [p for p in role['depends_on'] if p['when'].get('value') != companion]
    use['profile_fingerprint'] = review['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='lost a required dependency'):
        validate((review, occurrence, role, use))


@pytest.mark.parametrize(('pid', 'oid', 'name'), SPECS)
def test_registered_warlock_socketed_helmet_preserves_configuration(pid, oid, name):
    _, occurrence, role, use = records(pid, oid, name)
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == oid
    ]
    assert len(matches) == 1
    assert matches[0]['profile_id'] == pid
    assert matches[0]['required_predicates'] == role['must']['all']
    assert matches[0]['required_dependencies'] == [d['when'] for d in role.get('depends_on', [])]
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
