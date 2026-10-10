"""The fast hotkey sender speaks the workers' datagram dialect without importing them."""

import socket

from inventory_tracking import request
from inventory_tracking.appraisal import service


def test_prefixes_are_the_workers_own():
    assert request.PREFIXES == {
        'appraise': '',
        'collect': service.REQUEST_PREFIX,
        'equipped': service.EQUIPMENT_PREFIX,
        'disagree': 'disagree ',
        'shop': service.SHOP_PREFIX,
        'level': service.LEVEL_PREFIX,
        'macro': service.MACRO_PREFIX,
        'teleport': service.TELEPORT_PREFIX,
        'hunt-elites': service.HUNT_ELITES_PREFIX,
        'hunt-any': service.HUNT_ANY_PREFIX,
    }


def test_the_datagram_is_the_prefix_and_the_monotonic_stamp(tmp_path):
    endpoint = tmp_path / 'service.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(1)
        assert request.send('teleport', endpoint, clock=lambda: 12.5)
        assert server.recv(64) == b'teleport 12.5'
        assert request.main(['appraise', '--socket', str(endpoint)]) == 0
        assert server.recv(64).replace(b'.', b'').isdigit()


def test_without_a_service_the_sender_says_so(monkeypatch, tmp_path):
    told = []
    monkeypatch.setattr(request.subprocess, 'run', lambda *a, **k: told.append(a[0][2:]))
    assert request.main(['teleport', '--socket', str(tmp_path / 'none.sock')]) == 1
    assert len(told) == 1
    assert 'not running' in told[0][0]


def test_the_sender_runs_without_the_package_or_site_packages():
    import subprocess
    import sys

    done = subprocess.run([sys.executable, '-S', request.__file__, '--help'], capture_output=True, timeout=10)
    assert done.returncode == 0
