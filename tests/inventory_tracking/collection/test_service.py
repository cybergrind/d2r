"""Win+S / Win+D request handling: freshness, focus, scope, serialization and reporting."""

import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from inventory_tracking.appraisal import service as appraisal_service
from inventory_tracking.collection import service as collection_service
from inventory_tracking.collection.models import CaptureSummary, Character, CharacterStats


class Source:
    def __init__(self):
        self.pid, self.images, self.capture = 7, {'identity': {'pid': 7, 'start_ticks': '1'}}, {'x': 1}
        self.connected = 0

    def ensure_connected(self):
        self.connected += 1


def fake_record(directory, report, record, database, html=None):
    scope = record.get('scope', 'all')
    if scope == 'equipment':
        build = SimpleNamespace(
            character=Character(name='MuleOne', class_name='Warlock', level=9),
            tabs={},
            issues=[],
            scope=scope,
            sightings=[
                SimpleNamespace(location=SimpleNamespace(container=c)) for c in ('equipped', 'equipped', 'mercenary')
            ],
        )
        return build, CaptureSummary(total=3, new=3, moved=0, unchanged=0, gone=0)
    build = SimpleNamespace(
        character=Character(name='MuleOne', class_name='Warlock', level=9),
        character_stats=CharacterStats(
            level=9, strength=30, dexterity=25, vitality=40, energy=20, life_max=210, mana_max=60, defense=44
        ),
        tabs={1: 1, 2: 2},
        issues=['x'],
        scope=scope,
    )
    return build, CaptureSummary(total=3, new=1, moved=0, unchanged=2, gone=0)


@pytest.fixture
def parts(tmp_path):
    notifications = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        collector = collection_service.Collector(
            Source(),
            tmp_path / 'collection.sqlite',
            tmp_path / 'runs',
            pool,
            html=tmp_path / 'collection.html',
            capture_lock=threading.Lock(),
            focused=lambda images: True,
            notify=lambda title, body: notifications.append((title, body)),
            collect=lambda pid, images, capture, scope='all': {'pid': pid, 'timing': {}, 'location': 1, 'scope': scope},
            record=fake_record,
        )
        yield collector, notifications, tmp_path


def wait(collector):
    assert collector.future is not None
    collector.future.result(timeout=5)


def test_fresh_request_collects_records_and_notifies(parts):
    collector, notifications, tmp_path = parts
    assert collector.request(100.0, 100.5)
    wait(collector)
    run_dir = next((tmp_path / 'runs').iterdir())
    assert notifications == [
        (
            'MuleOne: 3 items · 1 new · 0 moved · 0 gone',
            '2 shared tabs; 1 issues\nLevel 9: str 30, dex 25, vit 40, ene 20; life 210, mana 60, defense 44'
            f'\nPage: {tmp_path / "collection.html"}\nReport: {run_dir}',
        )
    ]
    report = json.loads(next((tmp_path / 'runs').glob('*/report.json')).read_text())
    assert report['state'] == 'running' or report['state'] == 'complete'
    assert collector.source.connected == 1
    assert not collector.busy


def test_equipment_request_collects_only_worn_items_and_says_so(parts):
    collector, notifications, tmp_path = parts
    assert collector.request(100.0, 100.5, scope='equipment')
    wait(collector)
    run_dir = next((tmp_path / 'runs').iterdir())
    assert notifications == [
        (
            'MuleOne: 3 equipped items · 3 new · 0 moved · 0 gone',
            f'2 on the character, 1 on the mercenary\nPage: {tmp_path / "collection.html"}\nReport: {run_dir}',
        )
    ]
    report = json.loads((run_dir / 'report.json').read_text())
    assert report['scope'] == 'equipment'


def test_stale_and_rapid_requests_are_ignored(parts):
    collector, _, _ = parts
    assert not collector.request(100.0, 102.0)  # older than one second
    assert not collector.request(float('nan'), 100.0)
    assert collector.request(100.0, 100.2)
    assert not collector.request(100.5, 100.6)  # within the one-second debounce
    wait(collector)


def test_unfocused_game_rejects_with_a_failed_report_and_notification(parts, tmp_path):
    collector, notifications, _ = parts
    collector.focused = lambda images: False
    assert not collector.request(100.0, 100.1)
    report = json.loads(next((tmp_path / 'runs').glob('*/report.json')).read_text())
    assert (report['state'], report['error']) == ('failed', 'D2R is not focused')
    assert notifications == [('Collection unavailable', 'D2R is not focused')]
    assert not collector.busy


def test_memory_pass_failure_is_reported_and_releases_busy(parts, tmp_path):
    collector, notifications, _ = parts

    def fail(pid, images, capture, scope='all'):
        raise ValueError('items changed during the pass')

    collector.collect = fail
    assert not collector.request(100.0, 100.1)
    assert notifications[-1] == ('Collection unavailable', 'items changed during the pass')
    assert collector.request(102.0, 102.1) is False  # still failing, but accepted for a fresh attempt
    assert len(list((tmp_path / 'runs').iterdir())) == 2


def test_watcher_triggered_failures_are_logged_not_notified(parts, tmp_path):
    collector, notifications, _ = parts
    collector.focused = lambda images: False
    assert not collector.request(100.0, 100.1, trigger='stash-closed')
    report = json.loads(next((tmp_path / 'runs').glob('*/report.json')).read_text())
    assert (report['state'], report['trigger']) == ('failed', 'stash-closed')
    assert notifications == []
    collector.focused = lambda images: True
    assert collector.request(102.0, 102.1, trigger='stash-closed')
    wait(collector)
    assert notifications[0][0] == 'MuleOne: 3 items · 1 new · 0 moved · 0 gone'


def test_busy_collector_refuses_a_second_request(parts):
    collector, _, _ = parts
    started = threading.Event()
    release = threading.Event()

    def slow_record(directory, report, record, database, html=None):
        started.set()
        release.wait(5)
        return fake_record(directory, report, record, database, html)

    collector.record = slow_record
    assert collector.request(100.0, 100.1)
    started.wait(5)
    assert not collector.request(102.0, 102.1)
    release.set()
    wait(collector)
    assert collector.request(104.0, 104.1)
    wait(collector)


def test_dispatch_routes_collect_equipped_and_appraisal_datagrams():
    seen = []
    worker = SimpleNamespace(request=lambda t, now: seen.append(('appraise', t)) or True)
    collector = SimpleNamespace(request=lambda t, now, scope='all': seen.append((scope, t)) or True)
    assert appraisal_service.dispatch(b'12.5', 13.0, worker, collector)
    assert appraisal_service.dispatch(b'collect 12.5\n', 13.0, worker, collector)
    assert appraisal_service.dispatch(b'equipped 12.5\n', 13.0, worker, collector)
    assert not appraisal_service.dispatch(b'collect nope', 13.0, worker, collector)
    assert not appraisal_service.dispatch(b'equipped', 13.0, worker, collector)
    assert not appraisal_service.dispatch(b'\xff', 13.0, worker, collector)
    assert seen == [('appraise', 12.5), ('all', 12.5), ('equipment', 12.5)]


def test_request_collect_sends_the_collect_prefix(tmp_path):
    endpoint = tmp_path / 'request.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(1)
        assert appraisal_service.main(['request', '--collect', '--socket', str(endpoint)]) == 0
        message = server.recv(256).decode('ascii')
        assert message.startswith('collect ')
        assert float(message[8:]) > 0
        assert appraisal_service.main(['request', '--equipped', '--socket', str(endpoint)]) == 0
        message = server.recv(256).decode('ascii')
        assert message.startswith('equipped ')
        assert float(message[9:]) > 0
