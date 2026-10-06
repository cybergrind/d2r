import json
import socket

from inventory_tracking.appraisal import service as appraisal_service


def test_request_uses_local_socket_without_game_access(tmp_path):
    endpoint = tmp_path / 'request.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(1)
        assert appraisal_service.main(['request', '--socket', str(endpoint)]) == 0
        assert float(server.recv(256)) > 0


def test_attach_failure_publishes_completion_and_cleans_socket(tmp_path, monkeypatch):
    def fail(*args):
        raise ValueError('unsupported build')

    monkeypatch.setattr(appraisal_service.LiveReader, 'connect', fail)
    import pytest

    with pytest.raises(ValueError, match='unsupported build'):
        appraisal_service.main(
            [
                'serve',
                '--socket',
                str(tmp_path / 'request.sock'),
                '--output',
                str(tmp_path / 'runs'),
                '--database',
                str(tmp_path / 'unused.sqlite3'),
            ]
        )
    report = json.loads(next((tmp_path / 'runs').glob('*/report.json')).read_text())
    assert report['state'] == 'failed'
    assert report['finished_at']
    assert not (tmp_path / 'request.sock').exists()


def test_null_market_charm_publishes_text_and_notification(tmp_path, monkeypatch, caplog):
    import logging
    from pathlib import Path

    record = json.loads((Path(__file__).parents[1] / 'fixtures/appraisal_charm_result.json').read_text())
    notifications = []
    monkeypatch.setattr(appraisal_service, 'notify', lambda *args: notifications.append(args))
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        appraisal_service.publish_request(tmp_path, record)
    assert json.loads((tmp_path / 'latest.json').read_text())['state'] == 'complete'
    text = (tmp_path / 'request-1/appraisal.txt').read_text()
    assert '\n  +35 to Life\n  +4 to Mana\n' in text
    assert text in caplog.text
    assert notifications[0][0] == 'Large Charm — review required'
    assert '+35 to Life; +4 to Mana' in notifications[0][1]


def test_worker_defaults_to_publication_but_explicit_database_stays_legacy(tmp_path, monkeypatch):
    import pytest

    from pricing.knowledge.publication import DEFAULT_STORE

    seen = []
    monkeypatch.setattr(appraisal_service, 'serve', lambda args: seen.append(args) or 0)
    assert appraisal_service.main(['serve']) == 0
    assert seen[-1].publication_store == DEFAULT_STORE
    assert seen[-1].database is None
    database = tmp_path / 'legacy.sqlite3'
    assert appraisal_service.main(['serve', '--database', str(database)]) == 0
    assert seen[-1].database == database
    assert seen[-1].publication_store is None
    custom = tmp_path / 'bundles'
    assert appraisal_service.main(['serve', '--publication-store', str(custom)]) == 0
    assert seen[-1].publication_store == custom
    with pytest.raises(SystemExit):
        appraisal_service.main(['serve', '--database', str(database), '--publication-store', str(custom)])


def test_serve_waits_for_game_process_before_attaching(tmp_path, monkeypatch, capsys):
    import pytest

    from inventory_tracking.native.session import GameNotReady, GameProcessUnavailable

    attempts = []
    states = []

    def connect(self, directory):
        attempts.append(directory)
        if len(attempts) < 3:
            raise GameProcessUnavailable('Expected one D2R.exe process, found []')
        if len(attempts) < 5:
            (directory / 'image.bin').write_bytes(b'menu capture')
            raise GameNotReady('unit table unavailable; enter a game with a character')
        raise ValueError('unsupported build')

    def sleep(seconds):
        states.append(json.loads(next((tmp_path / 'runs').glob('*/report.json')).read_text())['state'])
        assert seconds == appraisal_service.APPRAISAL.reconnect_delay

    monkeypatch.setattr(appraisal_service.LiveReader, 'connect', connect)
    monkeypatch.setattr(appraisal_service.time, 'sleep', sleep)
    with pytest.raises(ValueError, match='unsupported build'):
        appraisal_service.main(
            [
                'serve',
                '--socket',
                str(tmp_path / 'request.sock'),
                '--output',
                str(tmp_path / 'runs'),
                '--database',
                str(tmp_path / 'unused.sqlite3'),
            ]
        )
    assert len(attempts) == 5
    assert states == ['waiting'] * 4
    out = capsys.readouterr().out
    assert out.count('Waiting for D2R.exe') == 1
    assert out.count('Waiting for a character in game') == 1
    report = json.loads(next((tmp_path / 'runs').glob('*/report.json')).read_text())
    assert report['state'] == 'failed'
    # Menu-time attachments are removed; the final (fatal) attempt's directory is kept as evidence.
    assert [path.exists() for path in attempts[2:]] == [False, False, True]


def test_reconnect_uses_fresh_capture_directory_even_after_partial_failure(tmp_path, monkeypatch):
    import pytest

    directories = []

    def connect(self, directory):
        directories.append(directory)
        with (directory / 'image.bin').open('xb') as stream:
            stream.write(f'capture-{len(directories)}'.encode())
        if len(directories) == 2:
            raise OSError('capture interrupted')
        return len(directories), {'identity': {'pid': len(directories)}}, {'status': 'captured'}

    def reconnect_sequence(connect, directory, report):
        assert connect()[0] == 1
        with pytest.raises(OSError, match='capture interrupted'):
            connect()
        assert connect()[0] == 3
        assert len(set(directories)) == 3
        assert [(path / 'image.bin').read_bytes() for path in directories] == [b'capture-1', b'capture-2', b'capture-3']
        raise ValueError('end reconnect exercise')

    monkeypatch.setattr(appraisal_service.LiveReader, 'connect', connect)
    monkeypatch.setattr(appraisal_service, 'wait_for_game', reconnect_sequence)
    with pytest.raises(ValueError, match='end reconnect exercise'):
        appraisal_service.main(
            [
                'serve',
                '--socket',
                str(tmp_path / 'request.sock'),
                '--output',
                str(tmp_path / 'runs'),
                '--database',
                str(tmp_path / 'unused.sqlite3'),
            ]
        )


class RecordingProcess:
    def __init__(self):
        self.calls = []

    def call(self, function, *args):
        self.calls.append((function, args))
        return {}


def test_keep_warm_lookup_replays_recent_items_in_turn(tmp_path):
    runs = (('20260101T000000Z-a', 'Ring'), ('20260102T000000Z-b', 'Amulet'), ('20260102T000001Z-b', 'Amulet'))
    for run, name in runs:  # the repeated Amulet is one warm-up item
        request = tmp_path / run / 'request-1'
        request.mkdir(parents=True)
        (request / 'frozen.json').write_text(json.dumps({'observation': {'item': {'name': name}}}))
    (tmp_path / '20260103T000000Z-c' / 'request-1').mkdir(parents=True)
    (tmp_path / '20260103T000000Z-c' / 'request-1' / 'frozen.json').write_text('{"selection": {}}')  # rejected request

    recent = appraisal_service.RecentObservations(appraisal_service.stored_observations(tmp_path))
    process = RecordingProcess()
    touch = appraisal_service.warm_lookup(None, tmp_path / 'index.sqlite', recent)
    for _ in range(3):
        touch(process)
    retrieve = appraisal_service.process_retrieval(process, None, tmp_path / 'index.sqlite', recent)
    retrieve({'item': {'name': 'Jewel'}})  # a real lookup joins the rotation
    for _ in range(3):
        touch(process)

    names = [args[0]['item']['name'] for _, args in process.calls]
    assert names[:4] == ['Amulet', 'Ring', 'Amulet', 'Jewel']  # newest stored request first
    assert sorted(names[4:]) == ['Amulet', 'Jewel', 'Ring']


def test_keep_warm_lookup_without_any_item_does_nothing(tmp_path):
    process = RecordingProcess()
    appraisal_service.warm_lookup(None, tmp_path / 'index.sqlite', appraisal_service.RecentObservations())(process)
    assert process.calls == []


def test_service_separates_detail_and_identify_warmup(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    primary = object()
    identify = [object(), object(), object()]
    seen = []
    monkeypatch.setattr(appraisal_service, 'wait_for_game', lambda *_: (123, {}, {}))
    monkeypatch.setattr(appraisal_service, 'hud_process', lambda *_: nullcontext())
    monkeypatch.setattr(appraisal_service, 'RetrievalProcess', lambda *_: nullcontext(primary))
    monkeypatch.setattr(
        appraisal_service, 'RetrievalGroup', lambda *_: nullcontext(SimpleNamespace(processes=identify))
    )

    def keep_warm(processes, touch, *, interval):
        seen.append(list(processes))
        if len(seen) == 2:
            # Stop before game-memory reads, once both independent warmers are wired.
            raise KeyboardInterrupt
        return nullcontext()

    monkeypatch.setattr(appraisal_service, 'KeepWarm', keep_warm)
    assert (
        appraisal_service.main(
            [
                'serve',
                '--socket',
                str(tmp_path / 'sock'),
                '--output',
                str(tmp_path / 'runs'),
                '--database',
                str(tmp_path / 'unused.sqlite3'),
            ]
        )
        == 0
    )
    assert seen == [[primary], identify]


def test_disagree_request_routes_only_fresh_messages(tmp_path):
    endpoint = tmp_path / 'request.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(1)
        assert appraisal_service.main(['request', '--disagree', '--socket', str(endpoint)]) == 0
        assert server.recv(256).startswith(b'disagree ')
    calls = []

    def handler():
        calls.append(True)
        return True

    assert appraisal_service.dispatch(b'disagree 10', 10.2, None, None, disagree=handler)
    assert not appraisal_service.dispatch(b'disagree 10', 12, None, None, disagree=handler)
    assert not appraisal_service.dispatch(b'disagree nan', 12, None, None, disagree=handler)
    assert calls == [True]


def test_identify_uses_fast_process_and_routes_unenabled_items_to_detail(tmp_path):
    from types import SimpleNamespace

    calls = []
    observation = {'item': {'name': 'test'}}
    pin = {'generation': 'pinned-generation'}
    backend = SimpleNamespace(pinned=lambda: pin)

    class Process:
        def __init__(self, result):
            self.result = result

        def call(self, function, *args):
            calls.append((self, function, args))
            return self.result

    fast = Process({'triage': {'verdict': 'vendor'}})
    detail = Process({'legacy': True})
    retrieve = appraisal_service.identify_retrieval(fast, detail, backend, tmp_path)
    assert retrieve(observation) == fast.result
    assert [p for p, _, _ in calls] == [fast]
    fast.result = None
    assert retrieve(observation) == detail.result
    assert [p for p, _, _ in calls] == [fast, fast, detail]
    assert calls[-1][2] == (observation, tmp_path, pin)


def test_identify_warmup_never_requests_legacy_detail():
    process = RecordingProcess()
    observation = {'item': {'name': 'Ring'}}
    recent = appraisal_service.RecentObservations([observation])
    appraisal_service.warm_identify_lookup(recent)(process)
    assert process.calls == [(appraisal_service.triage_warm, (observation,))]
