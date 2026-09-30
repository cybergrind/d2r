"""A pictured +3 Fissure roll is a preference, not minimum useful Lore."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_named_variant_links import validate


ROOT = Path(__file__).resolve().parents[5]
PREFERENCE = {
    'label': '+3 Fissure (planner target)',
    'when': {
        'op': 'stat_at_least',
        'key': '107:234',
        'value': 3,
        'absent_is_zero': True,
    },
}


@pytest.fixture(scope='module')
def records():
    def read(path):
        return json.loads((ROOT / path).read_text())

    role = next(
        p
        for p in read('pricing/data/appraisal-build-profiles.json')['profiles']
        if p['id'] == 'fissure-player-starter-lore'
    )
    occurrence = next(
        o
        for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences']
        if o['id'] == 'e2c80116e778f5a58e02b355'
    )
    use = next(
        u
        for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
        if u['profile_id'] == role['id']
    )
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': occurrence['id'],
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': role['id'],
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': 'Lore',
        'review_date': '2026-09-29',
        'reason': 'Starter prose prioritizes skills; positive Fissure is useful while pictured +3 is preferred. '
        'Completed nonethereal Lore pelt is required; usefulness is not a perfect-base or price claim.',
        'required_predicates': role['must']['all'],
        'required_preferences': [PREFERENCE],
    }
    return review, occurrence, role, use


@pytest.mark.parametrize('change', ['retained', 'removed', 'lowered', 'wrong-skill', 'malformed'])
def test_review_pins_preferred_roll_without_making_it_mandatory(records, change):
    review, occurrence, role, use = deepcopy(records)
    if change == 'removed':
        role['preferences'] = []
    elif change == 'lowered':
        role['preferences'][0]['when']['value'] = 1
    elif change == 'wrong-skill':
        role['preferences'][0]['when']['key'] = '107:233'
    elif change == 'malformed':
        review['required_preferences'] = [None]
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    if change == 'retained':
        assert validate((review, occurrence, role, use))['state'] == 'reviewed'
        assert {'op': 'stat_at_least', 'key': '107:234', 'value': 1, 'absent_is_zero': True} in review[
            'required_predicates'
        ]
    else:
        with pytest.raises(ValueError, match='preference'):
            validate((review, occurrence, role, use))


def test_registered_lore_source_keeps_reviewed_preference(records):
    rows = json.loads((ROOT / 'pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())['rows']
    matches = [row for row in rows if row['occurrence_id'] == records[1]['id']]
    assert len(matches) == 1
    assert matches[0]['required_preferences'] == [PREFERENCE]
    assert validate((matches[0], *records[1:]))['state'] == 'reviewed'
