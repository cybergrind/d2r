"""The Holy Bolt source is covered by the actual Ber configuration, not native armor."""

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import pin, read, validate
from tests.pricing.knowledge.assessment.maintenance.test_player_planner_endorsement import records as player_records


PID = 'fist-of-the-heavens-paladin-4-vipermagi-ber'
OID = '3db1f4eb689b273071b6d59f'


def current_records():
    review, occurrence, _, _ = player_records.__wrapped__()
    role = next(p for p in read('pricing/data/appraisal-build-profiles.json')['profiles'] if p['id'] == PID)
    use = next(
        u for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if u['profile_id'] == PID
    )
    review.update(
        profile_id=PID,
        profile_fingerprint=fingerprint(role),
        use_fingerprint=fingerprint(use),
        required_predicates=role['must']['all'],
        required_conditions=role['conditions'],
        reason=(
            'Guide Summary explicitly recommends Holy Bolt support. The exact player armor53 has Ber; '
            'reviewed rule requires that rune and one filled socket. Nonethereal-only review does not infer '
            'the omitted planner flag; no complete-loadout claim.'
        ),
    )
    review['planner_endorsement'].update(
        coverage='player_rune_socket_component', rune_definitions=pin('third-parties/d2data/json/gems.json')
    )
    review['planner_endorsement'].pop('socket_note')
    return review, occurrence, role, use


def test_registered_holy_bolt_armor_requires_actual_ber():
    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == OID
    ]
    assert len(rows) == 1
    review = rows[0]
    assert review['profile_id'] == PID
    assert review['planner_endorsement']['coverage'] == 'player_rune_socket_component'
    assert {'op': 'socket_runes_equal', 'value': ['Ber Rune']} in review['required_predicates']
    assert validate((review, *current_records()[1:]))['state'] == 'reviewed'
