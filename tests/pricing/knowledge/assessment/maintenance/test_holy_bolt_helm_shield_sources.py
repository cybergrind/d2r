"""Holy Bolt helm and shield preserve exact planner main/swap slot identity."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read, validate


SPECS = (
    ('harlequin-ber', '4ef89fd25e4ada45d6e7dd3e', 'head', '54'),
    ('herald-um-swap', 'a168afadcbbd203086fefb0f', 'larm2', '2'),
)


def current_records():
    template = next(
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] == 'fist-of-the-heavens-paladin-4-vipermagi-ber'
    )
    planner = decode_planner(read('pricing/raw/mr/planners/s10106pr.json'))
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    result = []
    for suffix, oid, slot, item_id in SPECS:
        role = next(p for p in profiles if p['id'] == 'fist-of-the-heavens-paladin-4-' + suffix)
        occurrence = next(o for o in occurrences if o['id'] == oid)
        use = next(u for u in uses if u['profile_id'] == role['id'])
        review = deepcopy(template)
        review.update(
            profile_id=role['id'],
            profile_fingerprint=fingerprint(role),
            canonical_name=role['names'][0],
            occurrence_id=oid,
            occurrence_fingerprint=fingerprint(occurrence),
            use_fingerprint=fingerprint(use),
            required_predicates=role['must']['all'],
            required_conditions=role['conditions'],
            reason=(
                'Explicit Holy Bolt guide recommendation and exact planner equipment slot; '
                'actual Ber helm or Um swap shield, nonethereal-only player review. '
                'No simultaneous main/swap bonuses or full-loadout claim.'
            ),
        )
        review['planner_endorsement'].update(slot=slot, item_id=item_id, expected_item=planner['items'][item_id])
        result.append((review, occurrence, role, use))
    return result


def test_exact_player_swap_slot_can_be_reviewed():
    for records in current_records():
        assert validate(records)['state'] == 'reviewed'


def test_swap_shield_cannot_be_reassigned_to_main_hand():
    records = current_records()[1]
    records[0]['planner_endorsement']['slot'] = 'larm'
    with pytest.raises(ValueError, match='equipment or wearer'):
        validate(records)


def test_registered_helm_and_swap_sources_preserve_runes():
    reviews = read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
    for _, occurrence, role, use in current_records():
        matching = [r for r in reviews if r['occurrence_id'] == occurrence['id']]
        assert len(matching) == 1
        assert matching[0]['required_predicates'] == role['must']['all']
        assert matching[0]['required_conditions'] == role['conditions']
        assert validate((matching[0], occurrence, role, use))['state'] == 'reviewed'
