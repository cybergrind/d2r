import threading
from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace

import pytest

from inventory_tracking.appraisal import published_backend
from pricing.knowledge.definition_store import fingerprint


class Publications:
    def __init__(self, index, failing=()):
        self.index, self.failing, self.calls = index, failing, []

    def get(self, generation, *, validate):
        self.calls.append((generation, validate))
        if generation in self.failing:
            raise ValueError(f'{generation} invalid')
        runtime = SimpleNamespace(generation=generation, database=self.index)
        return published_backend.Loaded(runtime, fingerprint(self.index.stat()))


@pytest.fixture
def setup(tmp_path, monkeypatch):
    index = tmp_path / 'index'
    index.write_bytes(b'index fixture')
    pointer = ['g1']
    monkeypatch.setattr(published_backend, 'pointer_generation', lambda _: pointer[0])
    monkeypatch.setattr(published_backend, 'published_snapshot', lambda _: nullcontext())
    monkeypatch.setattr(published_backend, 'retrieve_draft', lambda o, db, *, as_of: {'assessment': {'as_of': as_of}})
    publications = Publications(index, failing=('bad',))
    backend = published_backend.PublishedAppraisal(tmp_path, today=lambda: date(2026, 10, 2), publications=publications)
    backend.start()
    return backend, publications, pointer, index


def served(backend):
    with backend.request_scope():
        return backend.cache_context()[0]


def test_startup_validates_and_requests_pin_generation_date_and_issues(setup):
    backend, publications, _, _ = setup
    assert publications.calls == [('g1', True)]
    with backend.request_scope():
        assert backend.cache_context() == ('g1', '2026-10-02', ())
        result = backend.retrieve({'item': {}})
    assert result['assessment'] == {
        'as_of': date(2026, 10, 2),
        'publication_generation': 'g1',
        'publication_issues': [],
    }


def test_index_mutation_after_loading_is_rejected(setup):
    backend, _, _, index = setup
    index.write_bytes(b'changed')
    with pytest.raises(ValueError, match='index changed'), backend.request_scope():
        pass


def test_new_publication_is_served_only_after_the_processes_hold_it(setup):
    backend, publications, pointer, _ = setup
    during = []

    def prepare(generation):
        during.append((generation, served(backend)))  # a request while the processes load

    pointer[0] = 'g2'
    backend.refresh(prepare)
    assert during == [('g2', 'g1')]
    assert publications.calls[-1] == ('g2', False)  # validated by the first retrieval process
    assert served(backend) == 'g2'
    backend.refresh(lambda _: pytest.fail('same generation reloaded'))


def test_rejected_publication_keeps_the_served_one_until_the_pointer_moves(setup):
    backend, _, pointer, _ = setup
    pointer[0] = 'bad'
    backend.refresh()
    with backend.request_scope():
        assert backend.cache_context() == ('g1', '2026-10-02', ('Publication update unavailable: bad invalid',))
    backend.refresh(lambda _: pytest.fail('rejected generation retried'))
    pointer[0] = 'g1'
    backend.refresh()
    with backend.request_scope():
        assert backend.cache_context()[2] == ()


def test_processes_validate_once_then_reuse(monkeypatch):
    calls = []

    class Process:
        def __init__(self, name, ready_after):
            self.name, self.ready_after = name, ready_after

        def call(self, function, store, generation, validate):
            calls.append((self.name, generation, validate))
            self.ready_after -= 1
            return self.ready_after < 0

    prepare = published_backend.prepare_processes(
        [Process('appraisal', 1), Process('identify', 0)], 'store', stopped=threading.Event(), poll=0
    )
    prepare('g2')
    assert calls == [('appraisal', 'g2', True), ('appraisal', 'g2', True), ('identify', 'g2', False)]


def test_process_side_loads_in_background_and_reports_failure_once(tmp_path, monkeypatch):
    release = threading.Event()
    loaded = []

    class Slow(Publications):
        def get(self, generation, *, validate):
            release.wait(5)
            result = super().get(generation, validate=validate)
            loaded.append(generation)
            return result

        def holds(self, generation):
            return generation in loaded

    index = tmp_path / 'index'
    index.write_bytes(b'x')
    monkeypatch.setitem(published_backend._PROCESS_PUBLICATIONS, tmp_path, Slow(index, failing=('bad',)))
    assert not published_backend.prepare_publication(tmp_path, 'g2', True)
    assert not published_backend.prepare_publication(tmp_path, 'g2', True)
    release.set()
    published_backend._LOADING[tmp_path, 'g2'].result(timeout=5)
    assert published_backend.prepare_publication(tmp_path, 'g2', True)
    assert not published_backend.prepare_publication(tmp_path, 'bad', True)
    published_backend._LOADING[tmp_path, 'bad'].exception(timeout=5)
    with pytest.raises(ValueError, match='bad invalid'):
        published_backend.prepare_publication(tmp_path, 'bad', True)
    assert not published_backend.prepare_publication(tmp_path, 'bad', True)  # a later poll retries
    published_backend._LOADING.pop((tmp_path, 'bad')).exception(timeout=5)


def test_pinned_retrieval_uses_the_pinned_generation_or_refuses(setup, monkeypatch):
    backend, publications, _, index = setup
    with backend.request_scope():
        pinned = backend.pinned()
    monkeypatch.setitem(published_backend._PROCESS_PUBLICATIONS, pinned.store, publications)
    result = published_backend.retrieve_pinned(pinned, {})
    assert result['assessment']['publication_generation'] == 'g1'
    index.write_bytes(b'changed')
    with pytest.raises(ValueError, match='index changed'):
        published_backend.retrieve_pinned(pinned, {})
