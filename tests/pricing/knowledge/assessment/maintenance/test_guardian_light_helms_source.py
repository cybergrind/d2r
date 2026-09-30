"""Guardian's Light helmet recommendations retain their actual socket payload."""

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import read, validate
from tests.pricing.knowledge.assessment.maintenance.test_prose_named_alternatives import records as named_records


SPECS = (
    ('blessed-hammer-paladin-2-harlequin', 'e39be2ca8a581dfd7af4d91e'),
    ('berserk-barbarian-1-harlequin', 'df4a0ce2ddf84337ff38f74e'),
    ('abyss-warlock-build-guide-2-harlequin', 'c0b04da7ebc11cccf6264131'),
    ('echoing-strike-warlock-guide-2-harlequin', '929026f0f1a1fdaa8f1c881e'),
)


def records(intrinsic, oid):
    result = named_records(intrinsic + '-guardian-light', oid, 'Harlequin Crest')
    result[0]['reason'] = (
        "Variant explicitly prescribes Guardian's Light in Harlequin Crest. Require the actual linked "
        'named jewel with native minimum magic modifiers; preserve intrinsic helmet, class, ethereal '
        'and full-loadout qualifications. Perfect jewel rolls are optional. Weapon conversion is not '
        'assumed to benefit from magic skill damage, and the proc is not an active buff.'
    )
    return result


@pytest.mark.parametrize(('intrinsic', 'oid'), SPECS)
def test_guardian_light_configuration_has_exact_source(intrinsic, oid):
    assert validate(records(intrinsic, oid))['state'] == 'reviewed'


@pytest.mark.parametrize(('intrinsic', 'oid'), SPECS)
def test_socket_requirement_cannot_disappear_from_review(intrinsic, oid):
    review, occurrence, role, use = records(intrinsic, oid)
    role['must']['all'] = [p for p in role['must']['all'] if p.get('op') != 'socket_jewel_matches']
    use['profile_fingerprint'] = review['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match='lost mandatory reviewed predicates'):
        validate((review, occurrence, role, use))


@pytest.mark.parametrize(('intrinsic', 'oid'), SPECS)
def test_registered_socketed_helmet_preserves_exact_configuration(intrinsic, oid):
    _, occurrence, role, use = records(intrinsic, oid)
    matches = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['occurrence_id'] == oid
    ]
    assert len(matches) == 1
    assert matches[0]['profile_id'] == intrinsic + '-guardian-light'
    assert matches[0]['required_predicates'] == role['must']['all']
    assert matches[0]['required_conditions'] == role['conditions']
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
