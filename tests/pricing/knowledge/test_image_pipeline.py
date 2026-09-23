import socket

from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft


def test_draft_retains_unknown_facets_and_never_quotes_a_price(tmp_path, monkeypatch):
    import json

    source = tmp_path / 'corpus.json'
    source.write_text(json.dumps({'schema_version': 1, 'rows': [{'name': 'Amulet', 'kind': 'catalog'}]}))
    database = tmp_path / 'kb.sqlite3'
    build_index([source], database)
    monkeypatch.setattr(socket.socket, 'connect', lambda *a: (_ for _ in ()).throw(AssertionError('network')))
    draft = {'item': {'name': 'Amulet', 'sockets': None, 'rarity': None, 'affixes': []}, 'review': ['check image']}
    result = retrieve_draft(draft, database)
    assert result['queries'][0]['facets'] == {}
    assert result['decision']['price_status'] == 'unresolved'
    assert result['decision']['verdict'] == 'REVIEW'
    assert result['extraction'] == draft
    assert result['evidence']['identity']['status'] == 'known'


def test_skill_discovery_does_not_become_cross_base_price(tmp_path):
    import json

    source = tmp_path / 'corpus.json'
    source.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'rows': [
                    {'name': 'Other Base', 'kind': 'demand', 'properties': {'1577': 3}},
                    {'name': 'My Base', 'kind': 'catalog'},
                ],
            }
        )
    )
    database = tmp_path / 'kb.sqlite3'
    build_index([source], database)
    draft = {
        'item': {
            'name': 'My Base',
            'sockets': 3,
            'affixes': [
                {'property_id': '1577', 'value': 3, 'label': '+{{value}} to Test (Warlock Only)'},
            ],
        }
    }
    result = retrieve_draft(draft, database)
    assert result['queries'][0]['facets'] == {'sockets': 3, 'properties': {'1577': 3}}
    assert result['queries'][1]['facets'] == {'property_min': {'1577': 3}}
    assert result['decision']['price_status'] == 'unresolved'
