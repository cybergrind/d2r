from pricing.knowledge.bases import assess_base, bucket_matches


def base(**overrides):
    return dict(
        name='Test Base',
        base_name='Test Base',
        rarity='normal',
        sockets=4,
        ethereal=False,
        socket_contents='empty',
        affixes=[],
        **overrides,
    )


def test_history_never_becomes_verified_price_or_inherits_premium():
    item = base()
    assert bucket_matches('4os/noneth/normal', item)
    for bucket in (
        '4os/eth/normal',
        '4os/noneth/normal/15ed',
        '4os/noneth/normal/filled',
        '4os/noneth/normal/res45',
        '4os/noneth/normal/affixed',
    ):
        assert not bucket_matches(bucket, item)
    evidence = {
        'evidence': {
            'historical_market': [
                {
                    'bucket': '4os/noneth/normal',
                    'date': '2026-09-18',
                    'details': {'median_ist': 0.837, 'n_priced': 4},
                    'scope_status': 'legacy_unverified',
                }
            ]
        }
    }
    result = assess_base(item, evidence)
    assert result['price_status'] == 'historical_asks_only'
    assert result['historical_asks'][0]['details']['median_ist'] == 0.837
    assert not assess_base(dict(item, ethereal=None), evidence)['historical_asks']
    assert assess_base(dict(item, runeword='Spirit'), evidence) is None


def test_ed_resists_skills_and_contents_are_separate_comparisons():
    item = base()
    item.update(rarity='superior', affixes=[{'property_id': '425', 'value': 15}, {'property_id': '441', 'value': 45}])
    assert bucket_matches('4os/noneth/superior/15ed/res45', item)
    assert not bucket_matches('4os/noneth/superior/res45', item)
    assert not bucket_matches('4os/noneth/superior/15ed/res40-44', item)
    item['socket_contents'] = 'filled'
    assert not bucket_matches('4os/noneth/superior/15ed/res45', item)


def test_runtime_base_draft_keeps_matching_history_and_readable_price(tmp_path):
    import json

    from inventory_tracking.appraisal.text import format_appraisal
    from pricing.knowledge.index import build_index
    from pricing.knowledge.pipeline import retrieve_draft

    artifact = tmp_path / 'evidence.json'
    artifact.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {
                        'name': 'Test Base',
                        'kind': 'historical_market',
                        'sockets': 4,
                        'ethereal': False,
                        'rarity': 'normal',
                        'bucket': '4os/noneth/normal',
                        'date': '2026-09-18',
                        'details': {'median_ist': 0.837, 'n_priced': 4},
                    },
                    {
                        'name': 'Test Base',
                        'kind': 'historical_market',
                        'sockets': 4,
                        'ethereal': False,
                        'rarity': 'normal',
                        'bucket': '4os/noneth/normal/15ed',
                        'details': {'median_ist': 100},
                    },
                ],
            }
        )
    )
    db = tmp_path / 'index.sqlite3'
    build_index([artifact], db)
    result = retrieve_draft({'item': base()}, db)
    text = format_appraisal({'state': 'complete', 'request_id': 1, 'result': result})
    assert 'Historical buckets' not in text
    assert 'median 0.837' not in text
    assert 'median 100' not in text
    assert result['decision']['price_status'] == 'historical_asks_only'
    assert result['price_estimate']['estimate_ist'] is None
    assert len(result['evidence']['identity']['evidence']['historical_market']) == 1


def test_coverage_includes_uncached_bases_without_inventing_prices(tmp_path):
    import json

    from pricing.knowledge.bases import coverage

    data = tmp_path / 'pricing/data'
    data.mkdir(parents=True)
    (data / 'appraisal-catalog.json').write_text(
        json.dumps(
            {
                'rows': [
                    {
                        'name': 'Uncached Base',
                        'category': 'weapons',
                        'base_code': 'verified-fixture',
                        'details': {'max_sockets': 4},
                    },
                ]
            }
        )
    )
    (data / 'wp-b-prices.json').write_text(json.dumps({'_meta': {'pulled': '2026-09-18'}}))
    (data / 'wp-g-bases.json').write_text('{}')
    report = coverage(tmp_path)
    assert report['counts'] == {'unresearched': 1}
    assert report['bases'][0]['buckets'] == []
    assert report['bases'][0]['explicit_clean_priced_observations'] == 0
