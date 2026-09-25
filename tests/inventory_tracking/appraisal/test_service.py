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

    from inventory_tracking.native.session import GameProcessUnavailable

    attempts = []
    states = []

    def connect(*args):
        attempts.append(1)
        if len(attempts) < 3:
            raise GameProcessUnavailable('Expected one D2R.exe process, found []')
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
    assert len(attempts) == 3
    assert states == ['waiting', 'waiting']
    assert capsys.readouterr().out.count('Waiting for D2R.exe') == 1
    report = json.loads(next((tmp_path / 'runs').glob('*/report.json')).read_text())
    assert report['state'] == 'failed'


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
