from contextlib import contextmanager
from contextvars import ContextVar

from inventory_tracking.appraisal.worker import AppraisalWorker
from tests.inventory_tracking.appraisal.test_worker import Capture, Deferred


def test_request_generation_survives_async_retrieval_cache_and_hover_checks():
    active = ContextVar('test_generation', default=None)
    selected = ['old']
    seen = []

    @contextmanager
    def scope():
        token = active.set(selected[0])
        try:
            yield
        finally:
            active.reset(token)

    class ScopedCapture(Capture):
        def freeze(self):
            seen.append(('capture', active.get()))
            return super().freeze()

        def still_selected(self, frozen):
            seen.append(('selection', active.get()))
            return True

    def retrieve(observation):
        seen.append(('retrieve', active.get()))
        return {'generation': active.get()}

    pool, output = Deferred(), []
    worker = AppraisalWorker(
        ScopedCapture(),
        retrieve,
        output.append,
        pool,
        request_scope=scope,
        cache_context=active.get,
        display=lambda _: None,
        clock=lambda: 0,
    )
    worker.request(1, 1)
    assert active.get() is None
    selected[0] = 'new'
    pool.run(0)
    assert output[-1]['result']['generation'] == 'old'
    worker.tick()
    assert seen[-1] == ('selection', 'old')
    worker.request(2, 2)
    pool.run(1)
    assert output[-1]['result']['generation'] == 'new'
    assert not output[-1]['cache_hit']
    worker.request(3, 3)
    assert output[-1]['cache_hit']
    assert output[-1]['result']['generation'] == 'new'
    assert seen[-1] == ('selection', 'new')
    assert active.get() is None
