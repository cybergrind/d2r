import json

from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft


def test_rare_name_lookup_does_not_promote_nearby_rolls(tmp_path):
    path = tmp_path / 'evidence.json'
    rows = []
    for i, scope, life, price in [
        (1, 'verified', 32, 2),
        (2, 'rejected', 30, 100),
        (3, 'unknown', 30, 50),
        (4, 'verified', 100, 40),
    ]:
        rows.append(
            {
                'kind': 'market',
                'name': 'Ring',
                'rarity': 'rare',
                'seller_id': str(i),
                'scope_status': scope,
                'ask_ist': price,
                'unit_policy': 'single_item',
                'properties': {'418': life, '520': 10},
                'observed_at': '2026-09-18',
            }
        )
    path.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    db = tmp_path / 'kb.sqlite3'
    build_index([path], db)
    extraction = {
        'item': {
            'name': 'Random Generated Name',
            'base_name': 'Ring',
            'rarity': 'rare',
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'affixes': [
                {'property_id': '418', 'value': 30, 'label': '+{{value}} to Life'},
                {'property_id': '520', 'value': 10, 'label': '+{{value}}% Faster Cast Rate'},
            ],
        }
    }
    result = retrieve_draft(extraction, db)
    assert result['queries'][0]['name'] == 'Ring'
    assert result['price_estimate']['estimate_ist'] is None
    assert result['assessment']['contract'] is None
    assert result['assessment']['comparisons']['summary']['priced_sellers'] == 0


def test_normal_base_with_unknown_listing_facets_has_no_estimate(tmp_path):
    path = tmp_path / 'evidence.json'
    rows = []
    for i, eth, props, price in [(1, None, {}, 1), (2, True, {}, 100), (3, None, {'510': 15}, 50)]:
        rows.append(
            {
                'kind': 'market',
                'name': 'Test Base',
                'rarity': 'normal',
                'seller_id': str(i),
                'scope_status': 'verified',
                'ask_ist': price,
                'unit_policy': 'single_item',
                'sockets': 4,
                'ethereal': eth,
                'properties': props,
                'socket_contents': 'unknown',
            }
        )
    path.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    db = tmp_path / 'kb.sqlite3'
    build_index([path], db)
    result = retrieve_draft(
        {
            'item': {
                'name': 'Test Base',
                'rarity': 'normal',
                'ethereal': False,
                'sockets': 4,
                'socket_contents': 'empty',
                'affixes': [],
            }
        },
        db,
    )
    assert result['price_estimate']['estimate_ist'] is None
    assert result['price_estimate']['sellers'] == 0
