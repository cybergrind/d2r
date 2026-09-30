"""A useful Stormshield retains the actual Shael preparation requirement."""

from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.builds import decode_planner
from tests.pricing.knowledge.assessment.maintenance.test_chaos_enigma_source import records as enigma_records
from tests.pricing.knowledge.assessment.maintenance.test_planner_endorsement import pin, read, validate


PID = 'berserk-barbarian-4-stormshield'
OID = '123f1e633b756a719be50f2b'


def records():
    role = next(r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == PID)
    use = next(
        r for r in read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'] if r['profile_id'] == PID
    )
    occurrence = next(r for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if r['id'] == OID)
    evidence = deepcopy(enigma_records()[0]['planner_endorsement'])
    evidence.pop('recipe_sources')
    evidence.pop('ethereal_scope')
    evidence.update(
        coverage='player_rune_socket_preparation',
        slot='larm',
        item_id='52',
        expected_item=decode_planner(read(evidence['planner']['path']))['items']['52'],
    )
    evidence['rune_definitions'] = pin('third-parties/d2data/json/gems.json')
    evidence['preparation_note'] = (
        'Native shield remains useful; actual linked Shael is a separate preparation requirement. '
        'No complete blocking or damage-reduction setup inferred.'
    )
    review = {
        'pattern_kind': 'structured_named_variant',
        'occurrence_id': OID,
        'occurrence_fingerprint': fingerprint(occurrence),
        'profile_id': PID,
        'profile_fingerprint': fingerprint(role),
        'use_fingerprint': fingerprint(use),
        'canonical_name': 'Stormshield',
        'review_date': '2026-09-29',
        'reason': (
            'Explicit Chaos Prep endorsement; actual nonethereal Monarch with Shael. '
            'Native defense remains useful while the rune preparation is unmet or unknown.'
        ),
        'required_predicates': deepcopy(role['must']['all']),
        'required_conditions': deepcopy(role['conditions']),
        'required_dependencies': [deepcopy(dep['when']) for dep in role['depends_on']],
        'planner_endorsement': evidence,
    }
    return review, occurrence, role, use


def test_chaos_stormshield_can_be_reviewed_with_separate_rune_preparation():
    assert validate(records())['state'] == 'reviewed'


@pytest.mark.parametrize('change', ['removed', 'optional', 'different-rune'])
def test_preparation_must_keep_actual_shael_requirement(change):
    review, occurrence, role, use = records()
    if change == 'removed':
        role['depends_on'] = []
    elif change == 'optional':
        role['depends_on'][0]['when'] = {
            'any': [role['depends_on'][0]['when'], {'op': 'fact_eq', 'field': 'identified', 'value': True}]
        }
    else:
        role['depends_on'][0]['when']['value'] = ['Ist Rune']
    review['required_dependencies'] = [deepcopy(dep['when']) for dep in role['depends_on']]
    use['profile_fingerprint'] = review['profile_fingerprint'] = fingerprint(role)
    review['use_fingerprint'] = fingerprint(use)
    with pytest.raises(ValueError, match=r'[Pp]lanner|preparation'):
        validate((review, occurrence, role, use))


def test_preparation_review_requires_explicit_scope():
    data = records()
    data[0]['planner_endorsement'].pop('preparation_note')
    with pytest.raises(ValueError, match='Planner rune preparation'):
        validate(data)


def test_registered_chaos_stormshield_preserves_shael_dependency():
    _, occurrence, role, use = records()
    matches = [
        row
        for row in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if row['occurrence_id'] == OID
    ]
    assert len(matches) == 1
    assert matches[0]['required_dependencies'] == [dep['when'] for dep in role['depends_on']]
    assert matches[0]['required_conditions'] == role['conditions']
    assert validate((matches[0], occurrence, role, use))['state'] == 'reviewed'
