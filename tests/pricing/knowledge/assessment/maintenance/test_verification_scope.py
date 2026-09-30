"""Final attestations must expire when runtime behavior or its tests change."""

import pytest

from pricing.knowledge.assessment.maintenance import completion


def project(tmp_path, monkeypatch):
    for directory in ('pricing/knowledge', 'pricing/tools', 'inventory_tracking', 'tests/fixtures'):
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    for name in ('pyproject.toml', 'uv.lock'):
        (tmp_path / name).write_text('initial')
    monkeypatch.setattr(completion, 'ROOT', tmp_path)
    monkeypatch.setattr(completion, 'policy_fingerprint', lambda: 'review-policy')
    return lambda: completion.scope_fingerprint({}, {}, {}, None, ())


@pytest.mark.parametrize(
    'path',
    [
        'pricing/knowledge/pricing.py',
        'inventory_tracking/presentation.py',
        'tests/test_appraisal.py',
        'tests/fixtures/item.json',
        'pyproject.toml',
        'uv.lock',
    ],
)
def test_final_scope_changes_with_runtime_tests_fixtures_and_dependencies(tmp_path, monkeypatch, path):
    scope = project(tmp_path, monkeypatch)
    source = tmp_path / path
    source.write_text('original')
    before = scope()
    source.write_text('changed')
    assert scope() != before


def test_new_and_deleted_runtime_modules_change_scope_but_bytecode_does_not(tmp_path, monkeypatch):
    scope = project(tmp_path, monkeypatch)
    before = scope()
    source = tmp_path / 'pricing/knowledge/new_handler.py'
    source.write_text('new handler')
    added = scope()
    assert added != before
    cache = tmp_path / 'pricing/knowledge/__pycache__'
    cache.mkdir()
    (cache / 'new_handler.pyc').write_bytes(b'bytecode')
    assert scope() == added
    source.unlink()
    assert scope() == before


def test_generated_logs_and_kb_outputs_do_not_change_code_scope(tmp_path, monkeypatch):
    scope = project(tmp_path, monkeypatch)
    before = scope()
    for directory in ('inventory_tracking/runs', 'pricing/data', 'pricing/raw'):
        path = tmp_path / directory
        path.mkdir()
        (path / 'output.json').write_text('{"generated": true}')
    assert scope() == before


@pytest.mark.parametrize('missing', ['pyproject.toml', 'uv.lock'])
def test_missing_dependency_manifest_cannot_silently_shrink_scope(tmp_path, monkeypatch, missing):
    scope = project(tmp_path, monkeypatch)
    (tmp_path / missing).unlink()
    with pytest.raises(ValueError, match='Missing verification dependency'):
        scope()
