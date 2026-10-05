from pricing.triage.buyers import summarize


def listing(identity, owner, *, selling=False, ladder=False, **changes):
    return {
        'id': identity,
        'seller_id': owner,
        'item_id': '123',
        'amount': 1,
        'selling': selling,
        'active': True,
        'completed': False,
        'properties': [
            {'property_id': key, 'type': kind, kind: value}
            for key, kind, value in [
                (799, 'string', 'softcore'),
                (800, 'bool', ladder),
                (798, 'string', 'PC'),
                (1854, 'string', 'reign of the warlock'),
            ]
        ],
        **changes,
    }


def test_buyers_are_scoped_deduplicated_demand_not_prices():
    rows = [
        listing('a', 'buyer'),
        listing('b', 'buyer'),
        listing('c', 'other'),
        listing('sell', 'seller', selling=True),
        listing('ladder', 'ladder', ladder=True),
        listing('unknown', 'unknown', selling=None),
        listing('done', 'done', completed=True),
    ]
    documents = [('probe', {'_pulled_at': '2026-10-04T12:00:00Z', 'response': {'listings': rows}})]
    seen = []

    def cohort(row):
        seen.append(row)
        return row['name']

    report = summarize(documents, {'123': {'name': 'Jah Rune', 'type': 'runes'}}, cohort)
    assert report['cohorts']['Jah Rune']['buyers'] == 2
    assert report['cohorts']['Jah Rune']['listings'] == 3
    assert all(row['evidence_kind'] == 'buy' and row['ask_ist'] is None for row in seen)
    assert 'Unknown item' not in report['cohorts']


def test_unavailable_buy_query_does_not_establish_zero_buyers():
    report = summarize([('failed', {'error': 'HTTP 403'})], {}, lambda row: 'unused')
    assert report['cohorts'] == {}
    assert report['unavailable_sources'] == ['failed']
