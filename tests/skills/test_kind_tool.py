"""The loop kind tool (the d2-loop-watch skill's tools/kind.py) sends the `loop-kind` request the runner takes
(runner.py `choose_kind`), with the KP_6 kind picker in place too (2026-10-20)."""

import socket
import subprocess
import sys
import time
from pathlib import Path


TOOL = Path(__file__).resolve().parents[2] / '.agents' / 'skills' / 'd2-loop-watch' / 'tools' / 'kind.py'


def test_kind_sends_the_loop_kind_datagram(tmp_path):
    endpoint = tmp_path / 'macro.sock'
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.bind(str(endpoint))
        server.settimeout(10)
        before = time.monotonic()
        done = subprocess.run(
            [sys.executable, str(TOOL), '--socket', str(endpoint), 'tz'], capture_output=True, text=True, check=False
        )
        assert done.returncode == 0, done.stderr
        prefix, stamp, key = server.recv(256).decode('ascii').split()
    assert (prefix, key) == ('kind', 'tz')
    assert before <= float(stamp) <= time.monotonic()


def test_kind_without_a_key_is_refused():
    done = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, check=False)
    assert done.returncode == 2
