"""Set-piece source proof must preserve the full reviewed mercenary setup."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read, validate


TARGETS = (
    ('echoing-ubers-sazabi-sword', '21caa8b350bac49e5cbc044d'),
    ('echoing-ubers-sazabi-armor', 'b43b9748720c89e61de8ecf1'),
    ('echoing-ubers-sazabi-helm', '2f2cd9772b6c27905c79af26'),
)


def records(pid, oid):
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == pid)
    use = next(
        u for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if u['profile_id'] == pid
    )
    occurrence = next(o for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if o['id'] == oid)
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': oid,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': pid,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': role['names'][0],
        'review_date': '2026-09-29',
        'reason': (
            'Exact Ubers set component; preserve full-set companions, Act 5 Frenzy bearer and slot-specific '
            'Ber/Cham socket requirement. No set bonus or complete survival inferred from one piece.'
        ),
        'required_predicates': deepcopy(role['must']['all']),
        'required_conditions': deepcopy(role['conditions']),
        'required_setup': {key: deepcopy(role[key]) for key in ('required_rune', 'companions', 'mercenary_type')},
    }
    return review, occurrence, role, use


@pytest.mark.parametrize(('pid', 'oid'), TARGETS)
def test_exact_sazabi_component_validates_with_all_setup_requirements(pid, oid):
    assert validate(records(pid, oid))['state'] == 'reviewed'


@pytest.mark.parametrize('field', ['required_rune', 'companions', 'mercenary_type'])
def test_changed_setup_cannot_survive_refreshed_fingerprints(field):
    review, occurrence, role, use = records(*TARGETS[0])
    role[field] = [] if field == 'companions' else 'Other'
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match=r'named variant context|source equipment'):
        validate((review, occurrence, role, use))


def test_missing_setup_proof_cannot_be_treated_as_a_plain_candidate():
    review, occurrence, role, use = records(*TARGETS[0])
    del review['required_setup']
    with pytest.raises(ValueError, match=r'named variant context|source equipment'):
        validate((review, occurrence, role, use))


def test_agreeing_review_and_role_still_require_the_rune_in_the_source_label():
    review, occurrence, role, use = records(*TARGETS[0])
    review['required_setup']['required_rune'] = role['required_rune'] = 'Ist Rune'
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match=r'named variant context|source equipment'):
        validate((review, occurrence, role, use))


@pytest.mark.parametrize(('pid', 'oid'), TARGETS)
def test_sazabi_setup_source_is_registered(pid, oid):
    _review, occurrence, role, use = records(pid, oid)
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == oid
    ]
    assert len(matches) == 1
    assert matches[0]['profile_id'] == pid
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'


def test_companions_must_also_exist_in_the_pinned_variant_equipment():
    review, occurrence, role, use = records(*TARGETS[0])
    review['required_setup']['companions'] = role['companions'] = ['Unrelated set piece']
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='source equipment'):
        validate((review, occurrence, role, use))
