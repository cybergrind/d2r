from datetime import date
from pathlib import Path

from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.assessment.maintenance.replay import replay
from pricing.knowledge.publication import publish
from pricing.knowledge.published_runtime import retrieve_published, runtime_inputs


ROOT = Path(__file__).resolve().parents[3]


def test_published_retrieval_uses_only_bundle_inputs_and_restores_normal_readers(tmp_path, monkeypatch):
    from inventory_tracking.items import metadata as item_metadata
    from pricing.knowledge import artifacts, definition_store
    from pricing.knowledge.pipeline import retrieve_draft

    extraction = replay('superior_phase_blade')['extraction']
    baseline = retrieve_draft(extraction, DEFAULT_DATABASE, as_of=date(2026, 9, 24))
    bundle = publish(DEFAULT_DATABASE, repository=ROOT, store=tmp_path, extra_paths=runtime_inputs())
    original_read = artifacts._read

    def bundle_read(path):
        assert path.is_relative_to(bundle.directory), f'Unexpected working-tree read: {path}'
        return original_read(path)

    def forbidden():
        raise AssertionError('Default definitions/metadata must not load inside bundle appraisal')

    with monkeypatch.context() as patch:
        patch.setattr(artifacts, '_read', bundle_read)
        patch.setattr(definition_store.STORE, 'load', forbidden)
        patch.setattr(item_metadata, '_default_metadata', forbidden)
        # A pinned handle remains usable when the current pointer changes.
        (tmp_path / 'current.json').write_text('{"generation": "invalid replacement"}')
        result = retrieve_published(extraction, bundle, as_of=date(2026, 9, 24))
    assert result['assessment']['publication_generation'] == bundle.generation
    assert result['assessment']['base_uses'] == baseline['assessment']['base_uses']
    assert result['price_estimate'] == baseline['price_estimate']
    assert item_metadata.metadata()['bases']
    assert definition_store.catalog().generation == baseline['assessment']['definition_generation']


def test_metadata_dependent_base_cache_is_scoped_and_restored():
    import json

    from inventory_tracking.items.metadata import metadata, metadata_snapshot
    from pricing.knowledge.assessment.adapters.capture import bases_by_code

    document = json.loads(json.dumps(metadata()))
    base = next(iter(document['bases'].values()))
    code, original_name = base['code'], base['name']
    assert bases_by_code()[code]['name'] == original_name
    base['name'] = 'Published base fixture'
    with metadata_snapshot(json.dumps(document).encode()):
        assert bases_by_code()[code]['name'] == 'Published base fixture'
    assert bases_by_code()[code]['name'] == original_name


def test_supplied_artifacts_reject_missing_files_and_restore_after_failure(tmp_path):
    import pytest

    from pricing.knowledge.artifacts import artifact_snapshot, read_artifact, supplied_artifacts

    live = tmp_path / 'live.json'
    live.write_bytes(b'live')
    with pytest.raises(ValueError, match='absent from pinned publication'), supplied_artifacts({}):
        read_artifact(live)
    with (
        supplied_artifacts({}),
        pytest.raises(ValueError, match='absent from pinned publication'),
        artifact_snapshot([live]),
    ):
        pass
    assert read_artifact(live) == b'live'
