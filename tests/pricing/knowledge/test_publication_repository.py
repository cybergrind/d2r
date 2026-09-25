import json
from pathlib import Path

from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.publication import publish
from pricing.knowledge.publication_repository import PublicationRepository
from pricing.knowledge.published_runtime import runtime_inputs


ROOT = Path(__file__).resolve().parents[3]


def test_cached_runtime_survives_bad_pointer_without_reloading_artifacts(tmp_path, monkeypatch):
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge import artifacts
    from pricing.knowledge.published_runtime import published_snapshot

    bundle = publish(DEFAULT_DATABASE, repository=ROOT, store=tmp_path, extra_paths=runtime_inputs())
    repository = PublicationRepository(tmp_path)
    first = repository.load()
    assert first.runtime.generation == bundle.generation
    assert not first.issues

    def forbidden(path):
        raise AssertionError('Warm runtime must not reread artifacts')

    monkeypatch.setattr(artifacts, '_read', forbidden)
    assert repository.load().runtime is first.runtime
    with published_snapshot(first.runtime):
        assert metadata()['bases']
    (tmp_path / 'current.json').write_text('{broken')
    fallback = repository.load()
    assert fallback.runtime is first.runtime
    assert fallback.issues
    assert repository.load() == fallback
    (tmp_path / 'current.json').write_text(json.dumps({'generation': bundle.generation}))
    assert repository.load().runtime is first.runtime
    assert not repository.load().issues


def test_missing_initial_publication_and_mutated_last_good_index_are_unavailable(tmp_path):
    repository = PublicationRepository(tmp_path)
    assert repository.load().runtime is None
    bundle = publish(DEFAULT_DATABASE, repository=ROOT, store=tmp_path, extra_paths=runtime_inputs())
    assert repository.load().runtime is not None
    bundle.database.write_bytes(b'broken index')
    failed = repository.load()
    assert failed.runtime is None
    assert failed.issues
