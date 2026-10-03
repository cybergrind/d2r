from copy import deepcopy

import pytest

from pricing.knowledge.assessment.maintenance.windforce_market_review import audit, material_review


def listing():
    return {
        'id': 'a',
        'name': 'Windforce',
        'rarity': 'unique',
        'base_code': '6lw',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {'463': 8, '799': 'softcore', '800': False, '798': 'PC', '1854': 'reign of the warlock'},
        'scope_status': 'verified',
        'observed_at': '2026-10-03',
        'seller_id': 'seller',
        'ask_ist': 1,
        'amount': 1,
        'unit_policy': 'single_item',
        'evidence_kind': 'ask',
        'listing_status': {'active': True, 'selling': True, 'completed': False},
    }


@pytest.mark.parametrize('roll', [6, 7, 8])
def test_each_legal_roll_is_preserved_without_a_premium_claim(roll):
    row = listing()
    row['properties']['463'] = roll
    assert material_review(row) == {
        'status': 'verified_native_mana_steal',
        'native_mana_steal': roll,
        'socket_mana_steal': 0,
    }
    assert audit([row])['premium_threshold'] is None


@pytest.mark.parametrize('roll', [5, 9, True, 7.5, '8', None])
def test_illegal_or_missing_roll_is_not_perfect(roll):
    row = listing()
    row['properties']['463'] = roll
    assert material_review(row)['status'] != 'verified_native_mana_steal'


@pytest.mark.parametrize(
    ('insert', 'total', 'contribution'), [('Ort Rune', 8, 0), ('Vex Rune', 15, 7), ('Perfect Skull', 11, 3)]
)
def test_known_weapon_insert_is_subtracted(insert, total, contribution):
    row = listing()
    row.update(sockets=1, socket_contents='filled')
    row['properties'].update({'934': insert, '463': total})
    assert material_review(row) == {
        'status': 'verified_native_mana_steal',
        'native_mana_steal': 8,
        'socket_mana_steal': contribution,
    }


@pytest.mark.parametrize(
    'changes',
    [
        {'sockets': None},
        {'sockets': 2},
        {'sockets': True},
        {'socket_contents': 'unknown'},
        {'ethereal': True},
        {'ethereal': None},
        {'base_code': None},
    ],
)
def test_unknown_or_impossible_variant_does_not_enter_native_cohort(changes):
    row = listing()
    row.update(changes)
    assert material_review(row)['status'] != 'verified_native_mana_steal'


@pytest.mark.parametrize('insert', ['Jewel', 'Vex Rune, Ort Rune', None])
def test_incomplete_filled_payload_does_not_supply_native_roll(insert):
    row = listing()
    row.update(sockets=1, socket_contents='filled')
    row['properties']['934'] = insert
    assert material_review(row)['status'] == 'unknown_socket_payload'


def test_explicit_empty_payload_is_valid_but_conflicting_payload_is_not():
    row = listing()
    row['properties']['934'] = ''
    assert material_review(row)['native_mana_steal'] == 8
    row['properties']['934'] = 'Vex Rune'
    assert material_review(row)['status'] == 'unknown_socket_payload'


def test_unknown_payload_cannot_be_counted_as_exact_even_with_three_sellers():
    rows = [dict(listing(), id=str(i), seller_id=str(i), socket_contents='unknown') for i in range(3)]
    result = audit(rows)
    assert result['dated_material_asks'] == 0
    assert result['pricing_disposition'] == 'no_verified_material_comparisons'


def test_foreign_scope_is_excluded_even_if_cached_scope_says_verified():
    row = listing()
    row['properties']['800'] = True
    assert audit([row])['material_statuses'] == {'unverified_scope': 1}


def test_conflicting_duplicate_is_rejected():
    row = listing()
    other = deepcopy(row)
    other['properties']['463'] = 7
    with pytest.raises(ValueError, match='Conflicting duplicate'):
        audit([row, other])


@pytest.mark.parametrize(('field', 'value'), [('738', True), ('1216', True), ('402', 1), ('402', False)])
def test_explicit_variant_contradictions_fail_closed(field, value):
    row = listing()
    row['properties'][field] = value
    assert material_review(row)['status'] != 'verified_native_mana_steal'


def test_repeated_seller_does_not_establish_three_comparisons():
    result = audit([dict(listing(), id=str(i)) for i in range(3)])
    assert result['pricing_disposition'] == 'insufficient_material_sellers'
    assert result['material_cohorts'][0]['independent_sellers'] == 1


def test_different_payloads_are_not_pooled_for_seller_coverage():
    rows = [dict(listing(), id=str(i), seller_id=str(i)) for i in range(3)]
    rows[1]['sockets'] = 1
    rows[2].update(sockets=1, socket_contents='filled')
    rows[2]['properties'] = {**rows[2]['properties'], '934': 'Ort Rune'}
    result = audit(rows)
    assert result['pricing_disposition'] == 'insufficient_material_sellers'
    assert len(result['material_cohorts']) == 3
