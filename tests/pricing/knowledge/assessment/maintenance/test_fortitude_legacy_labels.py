"""Legacy planner wording cannot silently become a defense premium."""

import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.structured_named_variants import validate_link
from pricing.knowledge.assessment.maintenance.table_equivalence import _read, compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
LEGACY = (
    'Historical planner ebug labels do not establish extra defense or a premium; '
    'use actual captured defense and verified base/ethereal facts.'
)
BRANCHES = {
    'blizzard-sorceress-1-merc-fortitude': (
        'Standard prose cites Insight while its planner uses Infinity; armor utility does not '
        'resolve that weapon conflict.'
    ),
    'blizzard-sorceress-3-merc-fortitude': (
        'The Set variant uses Infinity, or Insight when Cold Rupture is equipped; verify the '
        'actual sunder/weapon branch separately.'
    ),
    'meteor-sorceress-1-merc-fortitude': (
        "The cited setup uses Infinity and Andariel's Visage; Conviction/immunity support "
        'comes from the weapon, not armor enhanced damage.'
    ),
    'lightning-sentry-assassin-1-merc-fortitude': (
        "The cited setup uses Infinity and Andariel's Visage; Conviction/immunity support "
        'comes from the weapon, not armor enhanced damage.'
    ),
}


def read(path):
    return json.loads((ROOT / path).read_text())


def evidence(pid):
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == pid)
    occurrence = next(
        r
        for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences']
        if r['source_id'] == role['source']['path']
        and r['source_locator'].startswith(role['source']['locator'] + '/')
        and r['side'] == 'merc'
        and r['slot'] == 'Body Armor'
        and 'ebug' in r['original_label']
    )
    use = next(
        u
        for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
        if u['profile_id'] == pid
        and u.get('source') == role['source']
        and not u.get('historical')
        and not u.get('source_coverage')
    )
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': occurrence['id'],
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': pid,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': 'Fortitude',
        'review_date': '2026-09-28',
        'reason': 'Exact armor component with legacy and weapon qualifications retained.',
        'required_predicates': role['must']['all'],
        'required_conditions': [LEGACY, BRANCHES[pid]],
    }
    return review, occurrence, role, use


@pytest.mark.parametrize('pid', BRANCHES)
@pytest.mark.parametrize('removed', [0, 1])
def test_revised_fortitude_profile_must_keep_legacy_and_weapon_qualifications(pid, removed):
    review, occurrence, role, use = evidence(pid)
    validate_link(review, occurrence, role, [use], ROOT, lambda pin: json.loads(_read(ROOT, pin)))
    role['conditions'].remove(review['required_conditions'][removed])
    review['profile_fingerprint'] = fingerprint(role)
    use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='required qualification'):
        validate_link(review, occurrence, role, [use], ROOT, lambda pin: json.loads(_read(ROOT, pin)))


def test_registered_legacy_fortitude_reviews_retain_qualified_component_scope():
    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in BRANCHES
    ]
    assert len(rows) == 4
    for row in rows:
        assert row['required_conditions'] == [LEGACY, BRANCHES[row['profile_id']]]
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert len(result) == 4
    assert all(r['state'] == 'reviewed' for r in result)
