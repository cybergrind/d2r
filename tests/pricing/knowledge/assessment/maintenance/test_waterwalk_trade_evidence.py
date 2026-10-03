from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.trade_waterwalk_evidence import audit


def row():
    return {
        'id': 'a',
        'name': 'Waterwalk',
        'rarity': 'unique',
        'seller_id': 'seller',
        'scope_status': 'verified',
        'observed_at': '2026-09-18',
        'evidence_kind': 'ask',
        'unit_policy': 'single_item',
        'amount': 1,
        'ask_ist': 5,
        'listing_status': {'active': True, 'selling': True, 'completed': False},
        'base_code': 'uvb',
        'sockets': 0,
        'socket_contents': 'empty',
        'ethereal': None,
        'properties': {
            '1854': 'reign of the warlock',
            '799': 'softcore',
            '800': False,
            '798': 'PC',
            '425': 210,
            '418': 65,
            '1855': 198,
        },
    }


def test_supported_cohort_deduplicates_observations_and_sellers():
    a = row()
    b = dict(a, id='b')
    result = audit([a, a, b])
    assert result['observations'] == 2
    assert result['supported']['sellers'] == ['seller']
    assert result['supported']['rows'] == ['a', 'b']


@pytest.mark.parametrize(
    ('field', 'value', 'reason'),
    [
        ('observed_at', None, 'undated'),
        ('amount', 2, 'ambiguous_unit'),
        ('ask_ist', 0, 'invalid_asking_terms'),
        ('seller_id', '', 'missing_seller'),
    ],
)
def test_ineligible_records_have_explicit_dispositions(field, value, reason):
    candidate = row()
    candidate[field] = value
    result = audit([candidate])
    assert result['excluded'] == {reason: ['a']}
    assert result['supported']['rows'] == []


def test_unknown_variant_remains_a_review_lead():
    candidate = row()
    candidate['properties'].pop('1855')
    result = audit([candidate])
    assert result['unproven'] == ['a']
    assert result['excluded'] == {}


def test_other_life_and_defense_rolls_remain_separate_cohorts():
    rows = []
    for i, (life, defense) in enumerate([(64, 198), (65, 195), (65, 201)]):
        r = row()
        r.update(id=str(i), seller_id=str(i))
        r['properties'].update({'418': life, '1855': defense})
        rows.append(r)
    result = audit(rows)
    assert len(result['unresolved_cohorts']) == 3
    assert result['supported']['rows'] == []


def test_conflicting_duplicate_is_not_silently_accepted():
    a = row()
    b = deepcopy(a)
    b['properties']['418'] = 64
    with pytest.raises(ValueError, match='Conflicting'):
        audit([a, b])


@pytest.mark.parametrize('properties', [{'800': True}, {'799': 'hardcore'}])
def test_foreign_modes_cannot_support_the_rule(properties):
    r = row()
    r['properties'].update(properties)
    assert audit([r])['excluded'] == {'unverified_scope': ['a']}


def test_original_asking_interest_is_separate_from_upgraded_cohort():
    r = row()
    r['base_code'] = 'xvb'
    r['properties'].update({'418': 45, '425': 195, '1855': 118})
    result = audit([r])
    assert result['original'] == {'rows': ['a'], 'sellers': ['seller']}
    assert result['supported']['rows'] == []
    assert result['unresolved_cohorts'] == []


def test_review_requires_independent_supported_sellers_and_no_new_dense_cohort():
    from pricing.knowledge.assessment.maintenance.trade_waterwalk_evidence import reviewed

    rows = []
    for i in range(3):
        upgraded = row()
        upgraded.update(id=f'u{i}', seller_id=str(i))
        original = deepcopy(upgraded)
        original.update(id=f'o{i}', base_code='xvb')
        original['properties']['1855'] = 124
        rows.extend([original, upgraded])
    evidence = audit(rows)
    assert reviewed(evidence)
    for mutation in ['seller', 'omitted', 'duplicate']:
        bad = deepcopy(evidence)
        if mutation == 'seller':
            bad['supported']['sellers'] = ['0']
        elif mutation == 'omitted':
            bad['unproven'] = ['omitted-from-count']
        else:
            bad['unproven'] = ['o0']
        assert not reviewed(bad)
    for i in range(3):
        alternative = deepcopy(rows[1])
        alternative.update(id=f'a{i}', seller_id=str(i))
        alternative['properties']['1855'] = 201
        rows.append(alternative)
    assert not reviewed(audit(rows))
