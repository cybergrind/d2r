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


def test_display_lease_hides_on_worker_stall_missing_or_bad_frame(tmp_path):
    from inventory_tracking.appraisal.overlay import read_display
    from inventory_tracking.reports import publish

    path = tmp_path / 'osd.json'
    assert read_display(path, 10) == []
    publish(path, {'checked_at': 10, 'lines': ['Ring', 'Price unknown']})
    assert read_display(path, 10.1) == ['Ring', 'Price unknown']
    assert read_display(path, 11.5) == []
    assert read_display(path, 9) == []
    path.write_text('{')
    assert read_display(path, 10) == []


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


def test_overlay_process_clears_and_reaps_on_service_failure(tmp_path, monkeypatch):
    from unittest.mock import Mock

    import pytest

    from inventory_tracking.appraisal import overlay

    process = Mock(returncode=0)
    monkeypatch.setattr(overlay.subprocess, 'Popen', Mock(return_value=process))
    with pytest.raises(RuntimeError, match='service failed'), overlay.overlay_process(tmp_path, True) as path:
        raise RuntimeError('service failed')
    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=3)
    assert overlay.read_display(path, overlay.time.monotonic()) == []


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
