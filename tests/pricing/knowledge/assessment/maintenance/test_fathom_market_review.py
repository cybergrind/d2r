import pytest

from pricing.knowledge.assessment.maintenance.fathom_market_review import cold_review


def row(total, insert=None, contents='unknown', sockets=None):
    props = {'747': total}
    if insert is not None:
        props['934'] = insert
    return {
        'name': "Death's Fathom",
        'rarity': 'unique',
        'base_code': 'obf',
        'socket_contents': contents,
        'sockets': sockets,
        'properties': props,
    }


@pytest.mark.parametrize(('total', 'bounds'), [(35, [30, 30]), (34, [29, 30]), (30, [25, 27]), (18, [15, 15])])
def test_single_cold_facet_bounds_native_roll_without_inventing_its_roll(total, bounds):
    result = cold_review(row(total, 'Rainbow Facet: Cold Death', 'filled'))
    assert result['native_cold_range'] == bounds
    assert result['status'] == 'bounded_cold_facet'


@pytest.mark.parametrize('total', [14, 15, 17, 36, True, 30.5])
def test_invalid_total_or_impossible_facet_sum_is_rejected(total):
    assert cold_review(row(total, 'Rainbow Facet: Cold Level-Up', 'filled'))['status'] == 'invalid_cold_total'


def test_explicit_empty_and_unknown_insert_are_distinct():
    assert cold_review(row(30, contents='empty', sockets=0))['native_cold_range'] == [30, 30]
    assert cold_review(row(30))['status'] == 'unknown_socket_contribution'
    assert cold_review(row(35, 'Jewel', 'filled'))['status'] == 'unknown_socket_contribution'
    assert cold_review(row(35, 'Rainbow Facet: Cold Death', 'filled', 0))['status'] == 'conflicting_variant'
    assert cold_review(row(35, 'Rainbow Facet: Fire Death', 'filled', 1))['status'] == 'unknown_socket_contribution'


def test_unrelated_cold_skill_tab_field_cannot_supply_cold_damage():
    item = row(30)
    item['properties'] = {'517': 30}
    assert cold_review(item)['status'] == 'missing_cold_skill_damage'


@pytest.mark.parametrize(
    'changes',
    [
        {'base_code': 'invalid'},
        {'sockets': True},
        {'sockets': 2},
        {'properties': {'747': 35, '934': 'Rainbow Facet: Cold Death', '402': 0}},
        {'properties': {'747': 35, '934': 'Rainbow Facet: Cold Death', '1216': True}},
    ],
)
def test_impossible_socket_or_base_evidence_cannot_prove_perfect_cold(changes):
    item = row(35, 'Rainbow Facet: Cold Death', 'filled')
    assert cold_review({**item, **changes})['status'] == 'conflicting_variant'


def test_census_deduplicates_identical_ids_and_rejects_conflicts():
    from pricing.knowledge.assessment.maintenance.fathom_market_review import audit

    item = {**row(30), 'id': 'one'}
    assert len(audit([item, item])['observations']) == 1
    with pytest.raises(ValueError, match='Conflicting Fathom'):
        audit([item, {**item, 'seller_id': 'different'}])
