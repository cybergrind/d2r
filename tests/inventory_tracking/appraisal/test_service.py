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
            ['serve', '--socket', str(tmp_path / 'request.sock'), '--output', str(tmp_path / 'runs')]
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
