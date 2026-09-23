import json

from pricing.knowledge.legacy import import_catalog, import_legacy


def test_catalog_uses_verified_codes_and_keeps_item_requirements(tmp_path):
    raw = tmp_path / 'pricing' / 'raw'
    raw.mkdir(parents=True)
    (raw / 'd2data-weapons.json').write_text(
        json.dumps(
            {
                'verified': {
                    'name': 'Test Base',
                    'code': 'verified',
                    'type': 'sword',
                    'gemsockets': 4,
                    'reqstr': 43,
                    'levelreq': 7,
                },
            }
        )
    )
    result = import_catalog(tmp_path)
    row = result['rows'][0]
    assert row['base_code'] == 'verified'
    assert row['details']['max_sockets'] == 4
    assert row['details']['required_level'] == 7
    assert row['source_id'] == result['sources'][0]['id']
    assert result['sources'][0]['sha256']


def test_legacy_market_is_not_promoted_to_verified_exact_price(tmp_path):
    data = tmp_path / 'pricing' / 'data'
    data.mkdir(parents=True)
    (data / 'wp-b-prices.json').write_text(
        json.dumps(
            {
                '_meta': {'pulled': '2026-09-18', 'scope_filter': 'unset kept'},
                'test-base': {
                    'name': 'Test Base',
                    'buckets': {
                        '4os/eth/normal': {'median_ist': 8, 'n_priced': 2, 'thin': False},
                    },
                },
            }
        )
    )
    result = import_legacy(tmp_path)
    row = result['rows'][0]
    assert row['kind'] == 'historical_market'
    assert row['scope_status'] == 'legacy_unverified'
    assert row['date'] == '2026-09-18'
    assert row['sockets'] == 4
    assert row['ethereal'] is True
    assert row['details']['n_priced'] == 2
    assert row['distinct_sellers'] is None
