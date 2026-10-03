from inventory_tracking.appraisal.worker import AppraisalWorker
from tests.inventory_tracking.appraisal.test_worker import Capture, Deferred


def make_worker(**options):
    pool, records, frames = Deferred(), [], []
    capture = Capture()
    now = [10.0]
    worker = AppraisalWorker(
        capture,
        lambda o: {'extraction': o},
        records.append,
        pool,
        display=frames.append,
        clock=lambda: now[0],
        **options,
    )
    return worker, capture, pool, records, frames, now


def test_display_requires_request_and_hides_on_hover_loss_without_reappearing(monkeypatch):
    worker, capture, pool, _, frames, _ = make_worker()
    worker.tick()
    assert not frames
    worker.request(1, 1)
    pool.run(0)
    assert frames[-1]['state'] == 'complete'
    monkeypatch.setattr(capture, 'still_selected', lambda _: False)
    worker.tick()
    assert frames[-1] is None
    monkeypatch.setattr(capture, 'still_selected', lambda _: True)
    worker.tick()
    assert frames[-1] is None


def test_timeout_starts_at_completion_and_repeated_hotkey_uses_cache():
    worker, _, pool, records, frames, now = make_worker(display_seconds=30, cache_seconds=60)
    worker.request(1, 1)
    pool.run(0)
    now[0] = 39.9
    worker.tick()
    assert frames[-1] is not None
    now[0] = 40
    worker.tick()
    assert frames[-1] is None
    worker.request(2, 2)
    assert len(pool.jobs) == 1
    assert records[-1]['cache_hit'] is True
    now[0] = 70
    worker.tick()
    assert frames[-1] is None
    worker.request(3, 3)
    assert len(pool.jobs) == 2


def test_changed_stats_and_kb_revision_miss_cache():
    revision = [1]
    worker, capture, pool, _, _, _ = make_worker(cache_context=lambda: revision[0])
    worker.request(1, 1)
    pool.run(0)
    revision[0] = 2
    worker.request(2, 2)
    assert len(pool.jobs) == 2
    pool.run(1)
    capture.freeze = lambda: {'observation': {'item': {'sockets': 2}}}
    worker.request(3, 3)
    assert len(pool.jobs) == 3


def test_cache_hit_rechecks_hover_and_new_request_clears_display(monkeypatch):
    worker, capture, pool, records, frames, _ = make_worker()
    worker.request(1, 1)
    pool.run(0)
    monkeypatch.setattr(capture, 'still_selected', lambda _: False)
    worker.request(2, 2)
    assert records[-1]['state'] == 'rejected'
    assert frames[-1] is None
    assert len(pool.jobs) == 1


def test_hover_probe_error_hides_visible_result(monkeypatch):
    worker, capture, pool, _, frames, _ = make_worker()
    worker.request(1, 1)
    pool.run(0)

    def unavailable(_):
        raise OSError('process ended')

    monkeypatch.setattr(capture, 'still_selected', unavailable)
    worker.tick()
    assert frames[-1] is None


def test_cache_key_ignores_capture_time_but_preserves_viewer_and_raw_facts():
    import copy

    from inventory_tracking.appraisal.cache import item_key

    frozen = {
        'observation': {
            'item': {'name': 'Ring'},
            'source': {'captured_at': 'yesterday', 'viewer_context': {'level': 70}},
            'unresolved_stats': [{'id': 999, 'raw': 1}],
        },
        'identity': {'pid': 1},
    }
    other = copy.deepcopy(frozen)
    other['observation']['source']['captured_at'] = 'today'
    assert item_key(other) == item_key(frozen)
    other['observation']['source']['viewer_context']['level'] = 71
    assert item_key(other) != item_key(frozen)
    other = copy.deepcopy(frozen)
    other['observation']['unresolved_stats'][0]['raw'] = 2
    assert item_key(other) != item_key(frozen)
    assert frozen['observation']['source']['captured_at'] == 'yesterday'


def test_cache_is_bounded_and_hit_does_not_extend_expiration():
    from inventory_tracking.appraisal.cache import ResultCache

    cache = ResultCache(seconds=10, capacity=2)
    cache.put('a', {'value': 1}, 0)
    cache.put('b', {'value': 2}, 1)
    returned = cache.get('a', 2)
    assert returned is not None
    returned['value'] = 99
    cache.put('c', {'value': 3}, 3)
    assert cache.get('b', 3) is None
    assert cache.get('a', 9) == {'value': 1}
    assert cache.get('a', 10) is None


def test_visible_card_rereads_hover_only_every_recheck_interval(monkeypatch):
    worker, capture, pool, _, frames, now = make_worker(recheck_seconds=0.5)
    probes = []
    worker.request(1, 1)
    pool.run(0)
    monkeypatch.setattr(capture, 'still_hovered', lambda frozen: probes.append(now[0]) or False)
    now[0] = 10.2
    worker.tick()
    assert not probes
    assert frames[-1] is not None  # republished between probes
    now[0] = 10.5
    worker.tick()
    assert probes == [10.5]
    assert frames[-1] is None
