"""The mixed-socket source review cannot lose its separately required Ber."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read, validate


PID = 'smite-paladin-2-crown-ages'
OID = '54b3c8d721dc99dde2a88e16'


def records():
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == PID)
    use = next(
        u for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if u['profile_id'] == PID
    )
    occurrence = next(o for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if o['id'] == OID)
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': OID,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': PID,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': 'Crown of Ages',
        'review_date': '2026-09-29',
        'reason': (
            "Exact High Investment Smite Crown: actual Ber and Protector's Stone remain required. "
            'Native minimum helmet rolls are useful; chance to trigger Fade does not mean active Fade, '
            'Life Tap or Crushing Blow.'
        ),
        'required_predicates': deepcopy(role['must']['all']),
        'required_dependencies': [deepcopy(d['when']) for d in role['depends_on']],
        'required_conditions': deepcopy(role['conditions']),
        'required_socket': {'required_rune': 'Ber Rune'},
    }
    return review, occurrence, role, use


def test_mixed_socket_source_accepts_actual_ber_and_protector_requirements():
    assert validate(records())['state'] == 'reviewed'


def test_removed_ber_requirement_cannot_hide_behind_new_fingerprints():
    review, occurrence, role, use = records()
    del role['required_rune']
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='required socket'):
        validate((review, occurrence, role, use))


def test_smite_crown_source_is_registered():
    _review, occurrence, role, use = records()
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    assert matches[0]['required_socket'] == {'required_rune': 'Ber Rune'}
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'


@pytest.mark.parametrize('socket', [{}, [], {'other': 'Ber Rune'}, {'required_rune': ''}])
def test_required_socket_proof_rejects_invalid_shape(socket):
    review, occurrence, role, use = records()
    review['required_socket'] = socket
    with pytest.raises(ValueError, match='required socket'):
        validate((review, occurrence, role, use))


def test_socket_must_also_match_the_pinned_equipment_label():
    review, occurrence, role, use = records()
    review['required_socket']['required_rune'] = role['required_rune'] = 'Ist Rune'
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='source label'):
        validate((review, occurrence, role, use))
