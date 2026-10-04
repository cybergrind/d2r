from pricing.triage.base_socket_inference import apply, compile_inferences
from tests.pricing.triage.test_bands import listing


def rows_for(sockets, prices, *, ethereal=False):
    return [
        listing(f'{sockets}-{ethereal}-{i}', price)
        | {
            'category': 'base',
            'base_code': 'fixture',
            'rarity': 'normal',
            'ethereal': ethereal,
            'sockets': sockets,
        }
        for i, price in enumerate(prices)
    ]


UTILITY = [
    {'base_code': 'fixture', 'sockets': 4, 'details': {'legality': 'verified_type_and_capacity', 'runeword': 'Example'}}
]


def test_missing_sockets_infer_only_unique_supported_distribution_match():
    rows = rows_for(0, [1, 1, 1]) + rows_for(4, [10, 10, 10]) + rows_for(None, [9, 10, 11])
    table = compile_inferences(rows, UTILITY)
    inferred = apply(rows[-1], table)
    assert inferred['sockets'] == 4
    assert inferred['facet_basis']['sockets']['kind'] == 'price_distribution_inference'
    assert rows[-1]['sockets'] is None
    assert apply(rows[0], table) == rows[0]
    assert apply(rows[-1] | {'ethereal': True}, table)['sockets'] is None


def test_overlapping_sparse_and_unmatched_distributions_remain_unknown():
    for zero, socketed, unknown in [
        ([10] * 3, [10] * 3, [10] * 3),
        ([1] * 2, [10] * 3, [10] * 3),
        ([1] * 3, [10] * 3, [100] * 3),
    ]:
        rows = rows_for(0, zero) + rows_for(4, socketed) + rows_for(None, unknown)
        table = compile_inferences(rows, UTILITY)
        assert apply(rows[-1], table)['sockets'] is None
        assert next(iter(table.values()))['inferred_sockets'] is None


def test_duplicate_seller_stock_cannot_establish_distribution():
    rows = rows_for(0, [1] * 3) + rows_for(4, [10] * 3) + rows_for(None, [10] * 3)
    rows = [r | {'seller_id': 'same'} if r['sockets'] is None else r for r in rows]
    table = compile_inferences(rows, UTILITY)
    assert apply(rows[-1], table)['sockets'] is None


def test_replay_reports_unknown_socket_exclusions_and_uses_saved_inference():
    from pricing.triage.replay import listing_score

    rows = rows_for(0, [1] * 3) + rows_for(4, [10] * 3) + rows_for(None, [10] * 3)
    tables = {'bands': {}, 'rules': {'keep_ist': 0.25, 'rows': []}, 'own': {'rows': []}}
    result = listing_score(rows, tables)
    assert result['overall']['priced'] == 6
    assert result['excluded_listings']['valuable_base_missing_sockets'] == 3
    assert result['excluded_distinct_sellers'] == 3
    tables['base_socket_inferences'] = compile_inferences(rows, UTILITY)
    result = listing_score(rows, tables)
    assert result['overall']['priced'] == 9
    assert result['excluded_listings'] == {}


def test_missing_socket_distribution_can_match_zero_without_touching_explicit_property():
    rows = rows_for(0, [1, 1, 1]) + rows_for(4, [10, 10, 10]) + rows_for(None, [1, 1, 1])
    table = compile_inferences(rows, UTILITY)
    assert apply(rows[-1], table)['sockets'] == 0
    explicit = rows[-1] | {'properties': rows[-1]['properties'] | {'402': 4}}
    assert apply(explicit, table) == explicit
