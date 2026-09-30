"""Tri-Brid's CBF ring source does not claim an attack-rating benefit for spells/Smite."""

from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read, validate
from tests.pricing.knowledge.assessment.maintenance.test_prose_named_alternatives import records as named_records


PID = 'fist-of-the-heavens-paladin-3-raven-frost'
OID = '90d8ef668330066db5bac7b7'


def records():
    result = named_records(PID, OID, 'Raven Frost')
    result[0]['reason'] = (
        'Tri-Brid table footnote and prose require Cannot Be Frozen for Baal/Diablo attack phases. '
        'Raven Frost supplies this utility without perfect Dexterity. Attack rating does not improve '
        'FoH, Blessed Hammer or Smite; ring choice and full casting/blocking setup remain conditional.'
    )
    return result


def test_registered_tribrid_ring_preserves_exact_attack_qualification():
    _, occurrence, role, use = records()
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    assert matches[0]['required_conditions'] == role['conditions']
    assert matches[0]['required_predicates'] == role['must']['all']
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
    stats = next(
        r for r in read('pricing/knowledge/assessment/rules/stat_use_reviews.json')['reviews'] if r['role_id'] == PID
    )
    assert '19:0' not in {p['key'] for p in stats['priorities']}
