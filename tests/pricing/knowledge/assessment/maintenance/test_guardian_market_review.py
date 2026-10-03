from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.guardian_market_review import audit, material_review


def listing():
    return {
        'id': 'a',
        'name': 'Guardian Angel',
        'rarity': 'unique',
        'base_code': 'ult',
        'base_upgrade': True,
        'ethereal': True,
        'sockets': 1,
        'socket_contents': 'filled',
        'properties': {
            '425': 196,
            '934': 'Perfect Topaz',
            '738': True,
            '1216': True,
            '799': 'softcore',
            '800': False,
            '798': 'PC',
            '1854': 'reign of the warlock',
        },
        'scope_status': 'verified',
        'observed_at': None,
        'seller_id': 's',
        'ask_ist': 8,
        'source': 'cache',
        'amount': 1,
        'unit_policy': 'single_item',
        'evidence_kind': 'ask',
        'listing_status': {'active': True, 'selling': True, 'completed': False},
    }


def test_invalid_topaz_ed_is_a_conflict_not_a_premium():
    row = listing()
    row['properties']['425'] = 2347
    assert material_review(row)['status'] == 'conflicting_enhanced_defense'


@pytest.mark.parametrize(('insert', 'total', 'native'), [('Perfect Topaz', 196, 196), ('Pul Rune', 230, 200)])
def test_known_insert_separates_native_ed(insert, total, native):
    row = listing()
    row['properties'].update({'934': insert, '425': total})
    assert material_review(row)['native_ed'] == native


@pytest.mark.parametrize('insert', [None, 'Jewel', 'Pul Rune, Ral Rune'])
def test_unspecified_or_incomplete_payload_does_not_prove_native_ed(insert):
    row = listing()
    row['properties']['934'] = insert
    assert material_review(row)['status'] == 'unknown_socket_payload'


def test_unknown_ethereal_and_base_are_not_inferred_from_defense():
    row = listing()
    row.update(base_code=None, ethereal=None)
    assert material_review(row)['status'] == 'unknown_or_conflicting_variant'


def test_undated_rows_cannot_enter_pricing_cohorts():
    rows = [dict(listing(), id=str(i), seller_id=str(i)) for i in range(3)]
    result = audit(rows)
    assert result['dated_eligible_asks'] == 0
    assert result['pricing_disposition'] == 'no_dated_comparable_evidence'
    assert result['material_statuses'] == {'verified_native_ed': 3}


def test_conflicting_duplicate_is_rejected():
    first = listing()
    second = deepcopy(first)
    second['properties']['425'] = 197
    with pytest.raises(ValueError, match='Conflicting duplicate'):
        audit([first, second])


@pytest.mark.parametrize(
    ('value', 'status'),
    [
        (179, 'conflicting_enhanced_defense'),
        (180, 'verified_native_ed'),
        (200, 'verified_native_ed'),
        (201, 'conflicting_enhanced_defense'),
        (True, 'conflicting_enhanced_defense'),
        (196.0, 'conflicting_enhanced_defense'),
        (None, 'missing_enhanced_defense'),
    ],
)
def test_native_integer_boundaries(value, status):
    row = listing()
    row['properties']['425'] = value
    assert material_review(row)['status'] == status


@pytest.mark.parametrize('field', ['738', '1216'])
def test_conflicting_explicit_variant_fails_closed(field):
    row = listing()
    row['properties'][field] = False
    assert material_review(row)['status'] == 'unknown_or_conflicting_variant'


def test_unknown_occupancy_is_not_empty():
    row = listing()
    row.update(sockets=0, socket_contents='unknown')
    row['properties'].pop('934')
    assert material_review(row)['status'] == 'unknown_socket_payload'
    row['socket_contents'] = 'empty'
    assert material_review(row)['native_ed'] == 196


def test_dated_sample_requires_further_exact_review_not_an_automatic_price():
    row = listing()
    row['observed_at'] = '2026-10-02T12:00:00Z'
    result = audit([row])
    assert result['dated_eligible_asks'] == 1
    assert result['pricing_disposition'] == 'requires_exact_comparison_review'
    assert result['premium_threshold'] is None
