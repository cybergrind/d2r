"""Test runs share the host with the game (user, 2026-10-15): the player may be playing while agents run the suites,
and parallel runs (eight agents at `-n 6`, a pricing worker at 1.5-5 GB) locked the host.

- No parallel tests: a run is one process. `-n`/`--numprocesses` is accepted and turned off here, before xdist
  reads it, so xdist starts no workers.
- One run at a time on the host: a run takes the one slot, a `flock` on `.test-slots/slot`, and waits while another
  run holds it; the lock goes when the run's process ends, however it ends.
- Priority: nice 19 and the lowest best-effort I/O priority. Not SCHED_IDLE or the idle I/O class: a process
  starved under them while holding a kernel or filesystem lock stalls everything waiting on that lock.

`D2R_TEST_PRIORITY=normal` keeps the usual priority, e.g. to measure the timing tests on a quiet host."""

import contextlib
import fcntl
import os
import subprocess
import time
from pathlib import Path

import pytest


SLOT = Path(__file__).resolve().parent.parent / '.test-slots' / 'slot'
WAIT = 1.0  # seconds between looks at the slot while another run holds it
_held: list[int] = []  # the open slot file: its lock lasts as long as this process


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_main(config: pytest.Config) -> None:
    if config.pluginmanager.hasplugin('xdist'):
        config.option.numprocesses = 0
        config.option.dist = 'no'
        config.option.tx = []


def lower_priority() -> None:
    os.nice(19 - os.nice(0))
    with contextlib.suppress(FileNotFoundError):  # without util-linux's ionice: the usual I/O priority
        subprocess.run(['ionice', '-c', '2', '-n', '7', '-p', str(os.getpid())], check=False, capture_output=True)


def take_slot() -> None:
    """The host's one test slot, held by this process until it ends; waits while another run holds it."""
    SLOT.parent.mkdir(exist_ok=True)
    handle = os.open(SLOT, os.O_RDWR | os.O_CREAT, 0o644)
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            time.sleep(WAIT)
            continue
        _held.append(handle)
        return


def pytest_configure(config: pytest.Config) -> None:
    if os.environ.get('D2R_TEST_PRIORITY') != 'normal':
        lower_priority()
    take_slot()
