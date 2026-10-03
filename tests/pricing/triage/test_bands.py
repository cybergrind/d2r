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
    assert build_bands(old, [])['bands'][0]['liquidity'] == 'liquid'
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


def test_undated_listings_do_not_veto_independently_dated_activity():
    rows = [listing(i) for i in range(50)]
    rows.append({**listing(50), 'listing_updated_at': None})
    assert build_bands(rows, [])['bands'][0]['liquidity'] == 'liquid'


def test_snapshot_selection_uses_instants_and_rejects_invalid_date_ranking():
    from pricing.triage.bands import latest_rows

    old = {**listing(1), 'observed_at': '2026-10-03T12:00:00+03:00', 'ask_ist': 100}
    new = {**old, 'observed_at': '2026-10-03T10:00:00Z', 'ask_ist': 1}
    invalid = {**old, 'observed_at': 'unknown'}
    assert latest_rows([new, old, invalid]) == [new]
    # Equal instants use actual listing update times, not their textual order.
    equivalent = {**new, 'observed_at': '2026-10-03T13:00:00+03:00', 'listing_updated_at': '2026-10-03T09:00:00+03:00'}
    updated = {**new, 'listing_updated_at': '2026-10-03T07:00:00Z'}
    assert latest_rows([updated, equivalent]) == [updated]
    naive = {**new, 'observed_at': '2026-10-03T11:00:00'}
    assert latest_rows([new, naive]) == [naive]


def test_band_dates_use_the_same_utc_calendar():
    from pricing.triage.bands import band_for

    rows = [
        {**listing(i), 'listing_updated_at': '2026-10-03T01:00:00+03:00', 'observed_at': '2026-10-04T01:00:00+03:00'}
        for i in range(10)
    ]
    band = band_for('uniques', 'Example', rows)
    assert band['newest_listing'] == '2026-10-02'
    assert band['observed_at'] == '2026-10-03'


def test_recent_independent_priced_sellers_outweigh_old_inventory():
    from pricing.triage.bands import band_for

    recent = [listing(f'recent-{i}') for i in range(10)]
    old = [listing(f'old-{i}') | {'listing_updated_at': '2026-09-01'} for i in range(50)]
    band = band_for('uniques', 'Example', recent + old)
    assert band['liquidity'] == 'liquid'
    assert band['recent_priced_sellers'] == 10
    assert band['listing_span_days'] > 14
    assert band_for('uniques', 'Example', recent[:9] + old)['liquidity'] == 'thin'
    copies = [recent[0] | {'listing_id': str(i)} for i in range(30)]
    assert band_for('uniques', 'Example', copies + old)['liquidity'] == 'thin'


def test_tightly_clustered_old_or_future_asks_cannot_establish_current_activity():
    from pricing.triage.bands import band_for

    for changed in ('2026-01-01', '2026-10-04', None):
        rows = [listing(i) | {'listing_updated_at': changed} for i in range(10)]
        assert band_for('uniques', 'Example', rows)['liquidity'] == 'thin'
    rows = [listing(i) | {'observed_at': None} for i in range(10)]
    assert band_for('uniques', 'Example', rows)['liquidity'] == 'thin'
