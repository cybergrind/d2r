from pricing.triage.bands import build_bands


def listing(seller, price=1, **changes):
    return dict(
        name='Example',
        category='uniques',
        listing_id=str(seller),
        seller_id=str(seller),
        evidence_kind='ask',
        scope_status='verified',
        unit_policy='single_item',
        amount=1,
        properties={'799': 'softcore', '800': False, '798': 'PC', '1854': 'reign of the warlock'},
        ask_ist=price,
        observed_at='2026-10-03',
        listing_updated_at='2026-10-02',
        prices=[{'type': 'runes', 'quantity': 1}],
        **changes,
    )


def test_bands_use_sellers_and_actual_listing_dates_not_fetch_dates():
    rows = [listing(i) for i in range(10)]
    rows += [{**rows[0], 'listing_id': 'another', 'ask_ist': 100}]
    band = next(b for b in build_bands(rows, [])['bands'] if b['bucket'] == 'name')
    assert band['sellers'] == 10
    assert band['median_ist'] == 1
    assert band['liquidity'] == 'liquid'
    old = [{**r, 'listing_updated_at': '2026-01-01' if i == 0 else '2026-10-02'} for i, r in enumerate(rows)]
    assert build_bands(old, [])['bands'][0]['liquidity'] == 'thin'
    missing = [{**r, 'listing_updated_at': None} for r in rows]
    assert build_bands(missing, [])['bands'][0]['liquidity'] == 'thin'


def test_foreign_scope_and_duplicate_snapshots_do_not_raise_liquidity():
    row = listing(1)
    rows = [row] * 10 + [{**listing(i), 'properties': {**row['properties'], '800': True}} for i in range(2, 12)]
    band = next(b for b in build_bands(rows, [])['bands'] if b['bucket'] == 'name')
    assert band['sellers'] == 1
    assert band['liquidity'] == 'none'


def test_catalog_members_without_prices_remain_explicit():
    doc = build_bands([], [{'name': 'Missing', 'type': 'sets'}])
    assert doc['bands'][0]['median_ist'] is None
    assert doc['bands'][0]['sellers'] == 0


def test_quantity_lots_do_not_set_single_item_band():
    single = [listing(i, 1) for i in range(3)]
    bulk = [{**listing(i, 0.1), 'amount': 40, 'unit_policy': 'stack_total'} for i in range(3, 13)]
    bands = {b['bucket']: b for b in build_bands(single + bulk, [])['bands']}
    assert bands['name']['median_ist'] == 1
    assert bands['name']['sellers'] == 3
    assert bands['quantity:40']['median_ist'] == 0.1
    assert bands['quantity:40']['quantity'] == 40


def test_unknown_listing_dates_cannot_hide_behind_fifty_known_dates():
    rows = [listing(i) for i in range(50)]
    rows.append({**listing(50), 'listing_updated_at': None})
    assert build_bands(rows, [])['bands'][0]['liquidity'] == 'thin'
