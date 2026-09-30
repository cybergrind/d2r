"""Bind the Enchant MF helmet to the actual named jewel in its source entry."""

from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read, validate
from tests.pricing.knowledge.assessment.maintenance.test_prose_named_alternatives import records as named_records


PID = 'enchant-sorceress-2-harlequin-defender-fire'
OID = 'e0a6c24ea7ef98943b432ad5'


def records():
    result = named_records(PID, OID, 'Harlequin Crest')
    result[0]['reason'] = (
        'Exact Magic Find helmet entry prescribes Defender Fire. Require actual linked named jewel '
        'and minimum native elemental modifiers; preserve class, base and ethereal guards. '
        'Wearer resistance reduction is not transferred to an enchanted ally; swap teleport '
        'FCR is not a helmet gate and the proc is not an assumed active buff.'
    )
    return result


def test_registered_enchant_socketed_helmet_keeps_payload_and_qualifications():
    _, occurrence, role, use = records()
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    assert matches[0]['profile_id'] == PID
    assert matches[0]['required_predicates'] == role['must']['all']
    assert matches[0]['required_conditions'] == role['conditions']
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
