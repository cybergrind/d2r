import json
from datetime import UTC, datetime

from pricing.knowledge.assessment.market_repository import market_rows
from pricing.knowledge.index import build_index
from pricing.knowledge.pipeline import retrieve_draft
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_appraisal_keeps_one_index_generation_during_atomic_rebuild(tmp_path, monkeypatch):
    import pricing.knowledge.pipeline as pipeline

    item = facts('Cinquedeas')
    rows = [
        {
            'kind': 'market',
            'name': item.name,
            'base_code': item.base_code,
            'rarity': 'normal',
            'ethereal': False,
            'sockets': 0,
            'socket_contents': 'empty',
            'properties': {},
            'scope_status': 'verified',
            'evidence_kind': 'ask',
            'unit_policy': 'single_item',
            'seller_id': str(i),
            'listing_id': str(i),
            'ask_ist': i,
            'observed_at': datetime.now(UTC).date().isoformat(),
        }
        for i in (1, 2, 3)
    ]
    source = tmp_path / 'rows.json'
    database = tmp_path / 'kb.sqlite3'
    source.write_text(json.dumps({'schema_version': 1, 'rows': rows}))
    build_index([source], database)
    lookup = pipeline.lookup

    def publish_between_queries(handle, *args, **kwargs):
        found = lookup(handle, *args, **kwargs)
        source.write_text(
            json.dumps({'schema_version': 1, 'rows': [{**r, 'ask_ist': r['ask_ist'] * 100} for r in rows]})
        )
        build_index([source], database)
        return found

    monkeypatch.setattr(pipeline, 'lookup', publish_between_queries)
    result = retrieve_draft(
        {'item': item.to_dict(), 'decoded_stats': [], 'source': {'stat_capture_complete': True}}, database
    )
    assert result['price_estimate']['estimate_ist'] == 2
    assert min(r['ask_ist'] for r in market_rows(database, item.name)) == 100


def test_appraisal_rejects_definition_index_generation_mismatch(tmp_path, monkeypatch):
    import pytest

    from pricing.knowledge import definition_store

    definitions = tmp_path / 'definitions.json'
    definitions.write_text(json.dumps({'schema_version': 1, 'rows': []}))
    database = tmp_path / 'kb.sqlite3'
    build_index([definitions], database)
    monkeypatch.setattr(definition_store, 'STORE', definition_store.DefinitionStore(definitions))
    definitions.write_text(json.dumps({'schema_version': 1, 'rows': [], 'revision': 'new'}))
    extraction = {'item': facts('Cinquedeas').to_dict(), 'decoded_stats': [], 'source': {'stat_capture_complete': True}}
    with pytest.raises(ValueError, match=r'definitions.*index.*rebuild'):
        retrieve_draft(extraction, database)
    build_index([definitions], database)
    result = retrieve_draft(extraction, database)
    assert result['assessment']['definition_generation'] == definition_store.catalog().generation


def test_appraisal_rejects_base_catalog_index_generation_mismatch(tmp_path, monkeypatch):
    import pytest

    from pricing.knowledge.assessment.mechanics import base_tiers

    catalog = tmp_path / 'catalog.json'
    catalog.write_text(json.dumps({'schema_version': 1, 'rows': []}))
    database = tmp_path / 'kb.sqlite3'
    build_index([catalog], database)
    monkeypatch.setattr(base_tiers, 'CATALOG', catalog)
    catalog.write_text(json.dumps({'schema_version': 1, 'rows': [], 'revision': 'new'}))
    extraction = {'item': facts('Cinquedeas').to_dict(), 'decoded_stats': [], 'source': {'stat_capture_complete': True}}
    with pytest.raises(ValueError, match=r'base catalog.*index.*rebuild'):
        retrieve_draft(extraction, database)
    build_index([catalog], database)
    result = retrieve_draft(extraction, database)
    assert str(catalog.resolve()) in result['assessment']['artifact_generations']


def test_appraisal_rejects_changed_leveling_artifacts_until_index_rebuilt(tmp_path, monkeypatch):
    import pytest

    from pricing.knowledge.assessment.policies import leveling

    paths = [tmp_path / name for name in ('appraisal-recommendations.json', 'appraisal-item-facts.json')]
    for path in paths:
        path.write_text(json.dumps({'schema_version': 1, 'rows': []}))
    database = tmp_path / 'kb.sqlite3'
    build_index(paths, database)
    monkeypatch.setattr(leveling, 'DATA', tmp_path)
    extraction = {'item': facts('Cinquedeas').to_dict(), 'decoded_stats': [], 'source': {'stat_capture_complete': True}}
    for path in paths:
        path.write_text(json.dumps({'schema_version': 1, 'rows': [], 'revision': 'new'}))
        with pytest.raises(ValueError, match=r'leveling.*index.*rebuild'):
            retrieve_draft(extraction, database)
        build_index(paths, database)
        result = retrieve_draft(extraction, database)
        assert str(path.resolve()) in result['assessment']['artifact_generations']
