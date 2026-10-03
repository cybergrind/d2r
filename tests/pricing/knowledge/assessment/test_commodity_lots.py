from datetime import date

from pricing.knowledge.assessment.commodities import bulk_quotes


def test_complete_set_quotes_never_accept_components_other_sets_or_quantity_lots():
    from pricing.knowledge.assessment.commodity_sets import set_quote

    base = {
        'name': '3x3 Key Set',
        'catalog_id': '3357156195',
        'category': 'misc',
        'evidence_kind': 'ask',
        'scope_status': 'verified',
        'unit_policy': 'single_item',
        'amount': 1,
        'ask_ist': 4,
        'observed_at': '2026-10-03',
        'listing_status': {'active': True, 'selling': True, 'completed': False},
        'properties': {'799': 'softcore', '800': False, '798': 'PC', '1854': 'reign of the warlock'},
    }
    rows = [dict(base, seller_id=str(i), listing_id=str(i)) for i in range(3)]
    rows += [
        dict(rows[0], name='Key of Terror', listing_id='component', seller_id='component'),
        dict(rows[0], catalog_id='1002230133766', listing_id='other-set', seller_id='other-set'),
        dict(rows[0], amount=3, listing_id='bulk', seller_id='bulk'),
        dict(rows[0], properties={**base['properties'], '800': True}, listing_id='ladder', seller_id='ladder'),
    ]
    rows += [
        dict(rows[0], listing_id=f'status-{i}', seller_id=f'status-{i}', ask_ist=0.01, listing_status=status)
        for i, status in enumerate(
            (
                {},
                {'active': False, 'selling': True},
                {'active': True, 'selling': False},
                {'active': True, 'selling': True, 'completed': True},
            )
        )
    ]
    quote = set_quote('3x3 Key Set', rows, today=date(2026, 10, 3))
    assert quote['estimate']['estimate_ist'] == 4
    assert quote['estimate']['sellers'] == 3
    assert quote['quantity_label'] == '3 of each key; 9 keys total'


def test_bulk_quotes_keep_lot_sizes_scope_and_unit_price_distinct():
    contract = {
        'policy': 'socket_material',
        'name': 'Jah Rune',
        'base_code': 'r31',
        'rarity': 'normal',
        'ethereal': False,
        'sockets': 0,
        'socket_contents': 'empty',
        'properties': {},
    }
    rows = [
        dict(
            contract,
            scope_status='verified',
            evidence_kind='ask',
            unit_policy='stack_total',
            amount=amount,
            ask_ist=price,
            seller_id=str(seller),
            listing_id=f'{amount}-{seller}',
            observed_at='2026-10-03',
        )
        for amount, price, seller in [(10, 8, 1), (10, 9, 2), (10, 10, 3), (2, 20, 4)]
    ]
    rows += [
        dict(rows[0], listing_id='foreign', scope_status='rejected', ask_ist=1),
        dict(rows[0], listing_id='ambiguous', unit_policy='ambiguous', ask_ist=1),
    ]
    quotes = bulk_quotes(contract, rows, today=date(2026, 10, 3))
    by_size = {q['quantity']: q for q in quotes}
    assert by_size[10]['estimate']['estimate_ist'] == 9
    assert by_size[10]['estimate']['sellers'] == 3
    assert by_size[2]['estimate']['estimate_ist'] is None
    assert by_size[2]['estimate']['sellers'] == 1
    assert bulk_quotes(dict(contract, policy='named'), rows, today=date(2026, 10, 3)) == []
    stale = bulk_quotes(contract, rows, today=date(2027, 10, 3))
    assert all(q['estimate']['estimate_ist'] is None for q in stale)
