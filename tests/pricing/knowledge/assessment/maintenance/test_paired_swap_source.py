"""Both swap slots can cite the same component without doubling its bonuses."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.structured_named_variants import validate_link
from pricing.knowledge.assessment.maintenance.table_equivalence import _read


ROOT = Path(__file__).resolve().parents[5]
ROLE = 'gold-find-barbarian-1-heart-oak'
OFFHAND = 'ee10ed272ee16c3b14ca1933'


@pytest.fixture
def records():
    def read(path):
        return json.loads((ROOT / path).read_text())

    role = next(p for p in read('pricing/data/appraisal-build-profiles.json')['profiles'] if p['id'] == ROLE)
    use = next(
        u for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if u['profile_id'] == ROLE
    )
    occurrence = next(
        o for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if o['id'] == OFFHAND
    )
    primary = next(
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] == ROLE and not r.get('paired_swap')
    )
    review = {
        **primary,
        'occurrence_id': OFFHAND,
        'occurrence_fingerprint': fingerprint(occurrence),
        'paired_swap': 'barbarian_hoto_component',
        'reason': (
            'The second identical swap-slot entry requires its own actual weapon; '
            'each contributes only its own +3 skills.'
        ),
    }
    return review, occurrence, role, use


def validate(records):
    review, occurrence, role, use = records
    return validate_link(review, occurrence, role, [use], ROOT, lambda pin: json.loads(_read(ROOT, pin)))


def test_second_swap_source_can_reference_one_weapon_component(records):
    result = validate(records)
    assert result['state'] == 'reviewed'
    assert result['profile_id'] == ROLE
    assert result['occurrence_id'] == OFFHAND
    assert 'combined_bonus' not in result


@pytest.mark.parametrize('change', ['absent', 'arbitrary-kind', 'main-hand', 'wrong-name', 'missing-qualification'])
def test_paired_source_cannot_bypass_unrelated_slot_or_item_guards(records, change):
    review, occurrence, role, use = deepcopy(records)
    if change == 'absent':
        review.pop('paired_swap')
    elif change == 'arbitrary-kind':
        review['paired_swap'] = 'any_slot'
    elif change == 'main-hand':
        occurrence['slot'] = 'Weapon'
        occurrence['source_locator'] = occurrence['source_locator'].replace('Off-Hand-Swap', 'Weapon')
    elif change == 'wrong-name':
        role['names'] = ['Call to Arms']
    else:
        role['conditions'] = role['conditions'][:-1]
    review['occurrence_fingerprint'] = fingerprint(occurrence)
    review['profile_fingerprint'] = fingerprint(role)
    use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match=r'context|paired|qualification'):
        validate((review, occurrence, role, use))


@pytest.mark.parametrize('change', ['other-offhand', 'multiple-weapons', 'other-class'])
def test_paired_swap_requires_two_identical_cited_slot_entries(records, change):
    from pricing.knowledge.assessment.maintenance.paired_swap_links import validate_pair

    review, occurrence, role, _ = records
    document = json.loads((ROOT / 'pricing/data/wp-a-builds.json').read_text())
    variant = document['gold-find-barbarian']['variants'][1]
    klass = 'Barbarian'
    if change == 'other-offhand':
        variant['player']['Off-Hand-Swap'] = ['Call to Arms']
    elif change == 'multiple-weapons':
        variant['player']['Weapon-Swap'] *= 2
    else:
        klass = 'Paladin'
    with pytest.raises(ValueError, match='paired swap'):
        validate_pair(review, occurrence, role, variant, klass, occurrence['original_label'])


def test_registered_secondary_slot_keeps_its_own_source_identity(records):
    document = json.loads((ROOT / 'pricing/knowledge/assessment/rules/table_equivalence_reviews.json').read_text())
    rows = [row for row in document['rows'] if row['occurrence_id'] == OFFHAND]
    assert len(rows) == 1
    assert rows[0]['paired_swap'] == 'barbarian_hoto_component'
    assert validate((rows[0], *records[1:]))['state'] == 'reviewed'
