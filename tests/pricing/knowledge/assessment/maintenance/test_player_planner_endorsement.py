"""Explicit player-component review cannot inherit the mercenary equipment map."""

import json
from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import (
    pin,
    read,
    records as merc_records,
    validate,
)


@pytest.fixture
def records():
    review, _, _, _ = merc_records.__wrapped__()
    role = deepcopy(
        next(
            p
            for p in read('pricing/data/appraisal-build-profiles.json')['profiles']
            if p['id'] == 'fist-of-the-heavens-paladin-4-vipermagi'
        )
    )
    occurrence = next(
        o
        for o in read('pricing/data/appraisal-guide-inventory.json')['occurrences']
        if o['id'] == '3db1f4eb689b273071b6d59f'
    )
    use = deepcopy(
        next(
            u
            for u in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
            if u['profile_id'] == role['id']
        )
    )
    # A native identity pin is required before this synthetic review can validate.
    role['source']['corroborating'].append({**pin('third-parties/d2data/json/uniqueitems.json'), 'locator': '/210'})
    use['source'] = role['source']
    use['profile_fingerprint'] = fingerprint(role)
    review.update(
        profile_id=role['id'],
        profile_fingerprint=fingerprint(role),
        occurrence_id=occurrence['id'],
        occurrence_fingerprint=fingerprint(occurrence),
        use_fingerprint=fingerprint(use),
        canonical_name='Skin of the Vipermagi',
        required_predicates=deepcopy(role['must']['all']),
        required_conditions=role['conditions'],
    )
    planner = json.loads(read('pricing/raw/mr/planners/s10106pr.json')['data'])['planner']
    evidence = review['planner_endorsement']
    evidence.update(
        coverage='player_intrinsic_component',
        slot='tors',
        item_id='53',
        expected_item=planner['items']['53'],
        ethereal_scope='nonethereal_only',
        socket_note='Planner53 has Ber; intrinsic armor review does not certify the socket configuration.',
    )
    evidence.pop('mercenary_id')
    evidence.pop('mercenary_type')
    return review, occurrence, role, use


@pytest.mark.parametrize(
    'change',
    [
        'retained',
        'mercenary-slot',
        'wrong-class',
        'missing-class-guard',
        'missing-ethereal-scope',
        'ethereal-role',
        'wrong-unique',
        'missing-socket-note',
        'complete-loadout',
    ],
)
def test_player_component_pins_wearer_identity_and_explicit_review_scope(records, change):
    review, _occurrence, role, use = records
    evidence = review['planner_endorsement']
    if change == 'mercenary-slot':
        evidence.update(
            item_id='29', expected_item=json.loads(read(evidence['planner']['path'])['data'])['planner']['items']['29']
        )
    elif change == 'wrong-class':
        evidence['player_class_code'] = 'sor'
    elif change == 'missing-class-guard':
        role['must']['all'] = [p for p in role['must']['all'] if p.get('field') != 'player_class']
        review['required_predicates'] = deepcopy(role['must']['all'])
    elif change == 'missing-ethereal-scope':
        evidence.pop('ethereal_scope')
    elif change == 'ethereal-role':
        role['must']['all'][2]['value'] = True
        review['required_predicates'] = deepcopy(role['must']['all'])
    elif change == 'wrong-unique':
        role['source']['corroborating'][-1]['locator'] = '/211'
    elif change == 'missing-socket-note':
        evidence['socket_note'] = ''
    elif change == 'complete-loadout':
        evidence['coverage'] = 'complete_loadout'
    review['profile_fingerprint'] = use['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    if change == 'retained':
        assert validate(records)['state'] == 'reviewed'
    else:
        with pytest.raises(ValueError, match=r'[Pp]lanner|[Ee]ndorse|[Nn]amed variant|[Ii]ntrinsic'):
            validate(records)


@pytest.mark.parametrize(
    ('item', 'scope', 'expected'),
    [
        ({}, None, False),
        ({}, 'nonethereal_only', True),
        ({'ethereal': None}, 'nonethereal_only', False),
        ({'ethereal': False}, None, True),
        ({'ethereal': True}, 'nonethereal_only', False),
        ({'ethereal': 0}, 'nonethereal_only', False),
    ],
)
def test_missing_planner_flag_is_not_silently_false(item, scope, expected):
    from pricing.knowledge.assessment.maintenance.planner_endorsement import ethereal_matches

    role = {'side': 'player', 'must': {'op': 'fact_eq', 'field': 'ethereal', 'value': False}}
    assert ethereal_matches(role, {'ethereal_scope': scope}, item) is expected
