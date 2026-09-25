from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace

import pytest

from inventory_tracking.appraisal import published_backend


def test_backend_freezes_generation_date_and_update_issues_for_one_request(tmp_path, monkeypatch):
    index = tmp_path / 'index'
    index.write_bytes(b'index fixture')
    runtime = SimpleNamespace(generation='old', database=index)
    loaded = SimpleNamespace(runtime=runtime, issues=('New publication rejected',))
    backend = published_backend.PublishedAppraisal(tmp_path, today=lambda: date(2026, 9, 25))
    monkeypatch.setattr(backend.repository, 'load', lambda: loaded)
    monkeypatch.setattr(published_backend, 'published_snapshot', lambda _: nullcontext())
    calls = []

    def retrieve(observation, database, *, as_of):
        calls.append((observation, database, as_of))
        return {'assessment': {}}

    monkeypatch.setattr(published_backend, 'retrieve_draft', retrieve)
    with backend.request_scope():
        loaded = SimpleNamespace(runtime=None, issues=('Changed pointer',))
        assert backend.cache_context() == ('old', '2026-09-25', ('New publication rejected',))
        result = backend.retrieve({'item': {}})
        assert result['assessment']['publication_generation'] == 'old'
        assert result['assessment']['publication_issues'] == ['New publication rejected']
        assert calls[0][1:] == (index, date(2026, 9, 25))
    with pytest.raises(ValueError, match='Changed pointer'), backend.request_scope():
        pass


def test_backend_rejects_index_mutation_after_capture(tmp_path, monkeypatch):
    index = tmp_path / 'index'
    index.write_bytes(b'old')
    backend = published_backend.PublishedAppraisal(tmp_path)
    monkeypatch.setattr(
        backend.repository,
        'load',
        lambda: SimpleNamespace(
            runtime=SimpleNamespace(generation='old', database=index),
            issues=(),
        ),
    )
    monkeypatch.setattr(published_backend, 'published_snapshot', lambda _: nullcontext())
    with backend.request_scope():
        index.write_bytes(b'changed')
        with pytest.raises(ValueError, match='index changed'):
            backend.retrieve({})
