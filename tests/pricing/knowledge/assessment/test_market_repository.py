import json

from pricing.knowledge.assessment.market_repository import market_rows
from pricing.knowledge.index import build_index


def test_repository_retrieves_exact_identity_market_rows_only_without_filtering_bad_evidence(tmp_path):
    rows = [
        {'id': 'z', 'kind': 'market', 'name': "Tal Rasha's Guardianship", 'scope_status': 'rejected'},
        {'id': 'a', 'kind': 'market', 'name': "Tal Rasha's Guardianship", 'scope_status': 'verified'},
        {'id': 'other', 'kind': 'market', 'name': "Tal Rasha's Guardianship bundle"},
        {'id': 'guide', 'kind': 'demand', 'name': "Tal Rasha's Guardianship"},
    ]
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    database = tmp_path / 'kb.sqlite3'
    build_index([source], database)
    result = market_rows(database, '  TAL RASHA\u2019S GUARDIANSHIP  ')
    assert {r['id'] for r in result} == {'a', 'z'}
    assert next(r for r in result if r['id'] == 'z')['scope_status'] == 'rejected'
    assert market_rows(database, "Tal Rasha's Guardianship") == result
    assert market_rows(database, 'Tal Rasha') == []
