"""Laying of Hands is a standalone set component, not an assumed full set."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_chaos_enigma_source import records as enigma_records
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import pin, read, validate


PID = 'berserk-barbarian-4-laying-hands'
OID = '0fb3b2bf4d93923b2a7ab648'


def records():
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == PID)
    use = next(
        r for r in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if r['profile_id'] == PID
    )
    occurrence = next(r for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if r['id'] == OID)
    evidence = deepcopy(enigma_records()[0]['planner_endorsement'])
    evidence.pop('recipe_sources')
    evidence.update(
        coverage='player_set_component',
        slot='glov',
        item_id='23',
        expected_item=decode_planner(read(evidence['planner']['path']))['items']['23'],
    )
    evidence['set_definitions'] = pin('third-parties/d2data/json/setitems.json')
    evidence['planner_definitions'] = pin('pricing/raw/mr/planners/game-data.json')
    evidence['component_note'] = 'Native glove stats only; no partial or complete Disciple set bonus claimed.'
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': OID,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': PID,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': 'Laying of Hands',
        'review_date': '2026-09-29',
        'reason': (
            'Chaos Prep explicitly endorsed; actual Bramble Mitts set component. Native IAS, demon damage '
            'and fire resistance are useful without companion set pieces.'
        ),
        'required_predicates': deepcopy(role['must']['all']),
        'required_conditions': deepcopy(role['conditions']),
        'planner_endorsement': evidence,
    }
    return review, occurrence, role, use


def test_explicit_chaos_prep_can_endorse_standalone_set_gloves():
    assert validate(records())['state'] == 'reviewed'


@pytest.mark.parametrize('field', ['component_note', 'ethereal_scope', 'slot', 'coverage'])
def test_set_component_scope_cannot_be_dropped_or_replaced(field):
    data = records()
    data[0]['planner_endorsement'][field] = ''
    with pytest.raises(ValueError, match=r'[Pp]lanner|[Ee]ndorsed'):
        validate(data)


@pytest.mark.parametrize('change', ['identity', 'base', 'set', 'socket', 'missing-pin'])
def test_native_set_proof_rejects_identity_or_socket_mismatch(change):
    from pricing.knowledge.assessment.maintenance.planner_set_endorsement import validate_set_component

    review, _, role, _ = records()
    evidence = review['planner_endorsement']
    item = deepcopy(evidence['expected_item'])
    tables = {pin['path']: read(pin['path']) for pin in (evidence['set_definitions'], evidence['planner_definitions'])}
    planned = tables[evidence['planner_definitions']['path']]['setItems']['set096']
    if change == 'identity':
        planned['index'] = 'Another Piece'
    elif change == 'base':
        planned['item'] = 'unknown'
    elif change == 'set':
        planned['set'] = 'Another Set'
    elif change == 'socket':
        item.update(sockets=1, socketedItems=['r13'])
    else:
        evidence.pop('set_definitions')
    with pytest.raises(ValueError, match='Planner set component'):
        validate_set_component(evidence, role, item, lambda ref: tables[ref['path']])


def test_registered_chaos_gloves_are_a_standalone_set_component():
    _, occurrence, role, use = records()
    matches = [
        row
        for row in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if row['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    assert matches[0]['required_conditions'] == role['conditions']
    assert matches[0]['required_predicates'] == role['must']['all']
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
