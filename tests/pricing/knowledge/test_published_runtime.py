from datetime import date
from pathlib import Path

from pricing.knowledge.__main__ import DEFAULT_DATABASE
from pricing.knowledge.assessment.maintenance.replay import replay
from pricing.knowledge.publication import publish
from pricing.knowledge.published_runtime import retrieve_published, runtime_inputs


ROOT = Path(__file__).resolve().parents[3]


def test_publication_rejects_stale_named_leveling_evidence(monkeypatch):
    import hashlib
    import json

    import pytest

    from pricing.knowledge import artifacts
    from pricing.knowledge.assessment.policies import named_leveling
    from pricing.knowledge.publication_validation import validate_runtime_inputs

    original_read = artifacts._read
    document = json.loads(original_read(named_leveling.RULES).data)
    document['inputs']['pricing/data/appraisal-item-facts.json'] = '0' * 64

    def stale_review(path):
        if path == named_leveling.RULES:
            raw = json.dumps(document).encode()
            return artifacts.Artifact(raw, hashlib.sha256(raw).hexdigest())
        return original_read(path)

    monkeypatch.setattr(artifacts, '_read', stale_review)
    with pytest.raises(ValueError, match='Named leveling evidence changed'):
        validate_runtime_inputs()


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


def test_a_validated_generation_is_validated_again_only_by_other_code(tmp_path, monkeypatch):
    import pytest

    from pricing.knowledge import publication_validation, published_runtime

    bundle = publish(DEFAULT_DATABASE, repository=ROOT, store=tmp_path, extra_paths=runtime_inputs())
    code, runs, failure = ['a'], [], []

    def validate():
        runs.append(code[0])
        if failure:
            raise ValueError(failure[0])

    monkeypatch.setattr(published_runtime, 'validation_code', lambda: code[0])
    monkeypatch.setattr(publication_validation, 'validate_runtime_inputs', validate)

    def load(**options):
        return published_runtime.load_runtime(bundle, **options)

    load(validate=False)
    assert runs == []
    load()
    load()  # a restart: the same bytes, checked by the same code
    assert runs == ['a']
    code[0] = 'b'  # edited validators have not seen this generation
    failure.append('rejected by the new code')
    with pytest.raises(ValueError, match='rejected by the new code'):
        load()
    failure.clear()
    load()  # a rejection leaves no record
    load()
    assert runs == ['a', 'b', 'b']
    # Records name the bytes they approved: a copied one from another generation counts for nothing.
    stamp = bundle.directory / published_runtime.VALIDATED
    stamp.write_text(stamp.read_text().replace(bundle.generation, '0' * 64))
    load()
    assert runs == ['a', 'b', 'b', 'b']


def test_validation_code_covers_the_modules_validation_runs(tmp_path):
    import subprocess
    import sys

    from pricing.knowledge import published_runtime

    first = published_runtime.validation_code()
    assert first == published_runtime.validation_code()
    script = (
        'import sys, pricing.knowledge.publication_validation, pricing.knowledge.published_runtime as runtime\n'
        'from pathlib import Path\n'
        'files = [Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, "__file__", None)]\n'
        'print(*[f for f in files if f.is_relative_to(runtime.ROOT) and ".venv" not in f.parts'
        ' and f not in runtime.validation_sources()])\n'
    )
    done = subprocess.run([sys.executable, '-c', script], cwd=ROOT, capture_output=True, text=True, check=True)
    assert done.stdout.split() == []
