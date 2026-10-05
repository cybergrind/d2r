from pricing.triage.turnover import compare


def row(identity, seller, price, variant='plain'):
    return {'listing_id': identity, 'seller_id': seller, 'ask_ist': price, 'variant': variant}


def page(rows, *, full=False, raw_ids=None, date='2026-10-04T12:00:00+00:00'):
    return {'rows': rows, 'all_ids': raw_ids or [r['listing_id'] for r in rows], 'full_page': full, 'observed_at': date}


def test_turnover_measures_gone_prices_and_new_sellers_without_calling_them_sales():
    before = {'board': page([row('a', 'one', 0.5), row('b', 'two', 2)], date='2026-10-03T12:00:00+00:00')}
    after = {'board': page([row('b', 'two', 2), row('c', 'three', 3)])}
    report = compare(before, after, lambda r: r['variant'])
    cohort = report['cohorts']['plain']
    assert cohort['disappeared'] == 1
    assert cohort['disappeared_share'] == 0.5
    assert cohort['new_sellers'] == 1
    assert cohort['gone_median_ist'] == 0.5
    assert cohort['retained_median_ist'] == 2
    assert cohort['uncensored_disappeared'] == 1


def test_unfinished_pull_cannot_count_missing_boards_as_disappearance():
    report = compare({'missing': page([row('a', 'one', 1)])}, {}, lambda r: r['variant'])
    assert report['cohorts'] == {}
    assert report['unobserved_boards'] == ['missing']


def test_page_zero_displacement_and_changed_scope_are_not_confirmed_absence():
    before = {'board': page([row('a', 'one', 1), row('b', 'two', 2)], date='2026-10-03T12:00:00+00:00')}
    after = {'board': page([row('c', 'three', 3)], full=True, raw_ids=['a', 'c'])}
    cohort = compare(before, after, lambda r: r['variant'])['cohorts']['plain']
    assert cohort['disappeared'] == 1  # a is still present, though no longer in this scope
    assert cohort['uncensored_disappeared'] == 0
    assert cohort['censored_disappeared'] == 1


def test_nonforward_snapshot_does_not_count_as_measurement():
    snapshots = {'board': page([row('a', 'one', 1)])}
    report = compare(snapshots, snapshots, lambda r: r['variant'])
    assert report['cohorts'] == {}
    assert report['invalid_intervals'] == ['board']


def test_snapshot_requires_scope_and_preserves_all_raw_ids_for_absence_checks(tmp_path):
    import json

    from pricing.triage.turnover import read_snapshot

    def listing(identity, ladder):
        return {
            'id': identity,
            'item_id': '123',
            'seller_id': identity,
            'amount': 1,
            'properties': [
                {'property_id': k, 'type': t, t: v}
                for k, t, v in [
                    (799, 'string', 'softcore'),
                    (800, 'bool', ladder),
                    (798, 'string', 'PC'),
                    (1854, 'string', 'reign of the warlock'),
                ]
            ],
            'prices': [{'name': 'Ist Rune', 'quantity': 1, 'group': 0}],
        }

    (tmp_path / '123-p0.json').write_text(
        json.dumps({'_pulled_at': '2026-10-04T12:00:00Z', 'listings': [listing('a', False), listing('b', True)]})
    )
    (tmp_path / '456-p0.json').write_text(json.dumps({'error': 'unavailable'}))
    catalog = {'123': {'name': 'Ist Rune', 'type': 'runes'}, '456': {'name': 'Mal Rune', 'type': 'runes'}}
    boards = read_snapshot(tmp_path, catalog, {'ist': 1})
    assert list(boards) == ['123']
    assert [r['listing_id'] for r in boards['123']['rows']] == ['a']
    assert boards['123']['all_ids'] == ['a', 'b']


def test_snapshot_reuses_same_bytes_but_renormalizes_changed_page(tmp_path, monkeypatch):
    import json

    from pricing.knowledge import market
    from pricing.triage.turnover import read_snapshot

    path = tmp_path / '123-p0.json'
    payload = {'_pulled_at': '2026-10-04T12:00:00Z', 'listings': [{'id': 'a', 'item_id': '123'}]}
    path.write_text(json.dumps(payload))
    calls = []

    def normalize(raw, **kwargs):
        calls.append(raw['id'])
        return {'listing_id': raw['id'], 'source': kwargs['source']}

    monkeypatch.setattr(market, 'normalize_listing', normalize)
    monkeypatch.setattr('pricing.triage.listing_defaults.normalize', lambda row: row)
    monkeypatch.setattr('pricing.triage.turnover.eligible', lambda row: True)
    catalog = {'123': {'name': 'Example', 'type': 'base'}}
    cache = {path.resolve(): (path.read_bytes(), [{'listing_id': 'a', 'source': 'relative'}])}
    cached = read_snapshot(tmp_path, catalog, {}, normalization_cache=cache)
    assert calls == []
    assert cached['123']['rows'] == [{'listing_id': 'a', 'source': str(path)}]
    payload['listings'][0]['id'] = 'b'  # even with the same collection timestamp
    path.write_text(json.dumps(payload))
    changed = read_snapshot(tmp_path, catalog, {}, normalization_cache=cache)
    assert calls == ['b']
    assert changed['123']['all_ids'] == ['b']
