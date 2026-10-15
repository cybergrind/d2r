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
        'pickup': service.PICKUP_PREFIX,
        'pad': service.PAD_PREFIX,
        'loop': service.LOOP_PREFIX,
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
        # A macro key also says how long its own process took to start, and the CPU of it.
        assert request.send('teleport', endpoint, clock=lambda: 12.5, began=(31.26, 12.04))
        assert server.recv(64) == b'teleport 12.5 31.3 12.0'
        assert request.send('level', endpoint, clock=lambda: 12.5, began=(31.26, 12.04))
        assert server.recv(64) == b'level 12.5'
        assert request.main(['pickup', '--socket', str(endpoint)]) == 0
        age, cpu = server.recv(64).split()[2:]
        assert float(cpu) >= 0
        assert float(age) >= 0


def test_without_a_service_the_sender_says_so(monkeypatch, tmp_path):
    told = []
    monkeypatch.setattr('subprocess.run', lambda *a, **k: told.append(a[0][2:]))
    assert request.main(['teleport', '--socket', str(tmp_path / 'none.sock')]) == 1
    assert len(told) == 1
    assert 'not running' in told[0][0]


def test_the_sender_runs_without_the_package_or_site_packages():
    import subprocess
    import sys

    done = subprocess.run([sys.executable, '-S', request.__file__, '--help'], capture_output=True, timeout=10)
    assert done.returncode == 0


def test_a_press_does_not_pay_for_modules_it_does_not_use():
    # 57 ms of every press went to the script's own start with argparse, subprocess and pathlib in it
    # (36 teleport presses with the game running, 21:26 on 2026-10-11).
    import subprocess
    import sys

    code = 'import runpy, sys; sys.argv = ["request.py", "--socket", "/nonexistent/none", "level"]\n'
    code += f'try:\n    runpy.run_path({request.__file__!r}, run_name="__main__")\nexcept SystemExit:\n    pass\n'
    code += 'print(sorted(set(sys.modules) & {"argparse", "pathlib", "re", "dataclasses", "inspect"}))'
    done = subprocess.run(
        [sys.executable, '-S', '-c', code], capture_output=True, text=True, timeout=10, env={'PATH': ''}
    )
    assert done.stdout.strip().splitlines()[-1] == '[]'


def test_a_wrong_kind_is_refused():
    assert request.main(['nothing']) == 2
    assert request.main([]) == 2
