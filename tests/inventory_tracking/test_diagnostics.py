"""Checks for actual memory reads and the sandbox/host file handoff."""

import ctypes
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from inventory_tracking.linux_process import executable_name
from inventory_tracking.memory import proc_read, vm_read
from inventory_tracking.probe import inspect_game
from inventory_tracking.reports import publish


def test_unnamed_readable_mapping_still_probes_memory():
    token = {'pid': os.getpid(), 'start_ticks': '1'}
    with (
        patch('inventory_tracking.probe.process_info', return_value={'identity': token}),
        patch('inventory_tracking.linux_process.Path.read_text', return_value='1000-2000 rw-p 0 00:00 0'),
        patch('inventory_tracking.probe.identity', return_value=token),
        patch('inventory_tracking.probe.fingerprint_executable', return_value={'error': 'not found'}),
        patch('inventory_tracking.probe.vm_read', return_value={'ok': True}) as read,
        patch('inventory_tracking.probe.proc_read', return_value={'ok': True}),
    ):
        result = inspect_game(os.getpid())
    assert result.get('memory_access'), 'A named PE mapping is not required to test memory permissions'
    read.assert_called_once_with(os.getpid(), 4096, 16)


def test_restart_during_fingerprinting_invalidates_successful_read():
    before = {'pid': os.getpid(), 'start_ticks': '1'}
    after = {'pid': os.getpid(), 'start_ticks': '2'}
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / 'D2R.exe'
        executable.write_bytes(b'fake executable')
        mapping = {'start': 4096, 'end': 8192, 'permissions': 'r--p', 'path': str(executable)}
        with (
            patch('inventory_tracking.probe.process_info', return_value={'identity': before}),
            patch('inventory_tracking.probe.process_mappings', return_value=[mapping]),
            patch('inventory_tracking.probe.identity', side_effect=[before, before, after]),
            patch('inventory_tracking.probe.vm_read', return_value={'ok': True}),
            patch('inventory_tracking.probe.proc_read', return_value={'ok': True}),
        ):
            result = inspect_game(os.getpid())
        assert not result['memory_access'], 'A restart during fingerprinting must invalidate the report'


def test_windows_process_names_exclude_launchers():
    assert executable_name(r'Z:\games\Diablo II Resurrected\D2R.exe') == 'd2r.exe'
    assert executable_name(r'c:\windows\system32\steam.exe') != 'd2r.exe'
    assert executable_name('/steam/Proton - Experimental/proton') != 'd2r.exe'


def check_child_read(reader):
    value = ctypes.create_string_buffer(b'diagnostic fixture')
    address = ctypes.addressof(value)
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(write_fd)
        os.read(read_fd, 1)
        os._exit(0)
    os.close(read_fd)
    try:
        result = reader(pid, address, 16)
        if result.get('errno') in (1, 13):
            pytest.skip(f'{reader.__name__} denied by execution environment: {result}')
        assert result.get('ok'), result
        assert result['bytes_read'] == 16
        assert 'data' not in result
    finally:
        os.close(write_fd)
        os.waitpid(pid, 0)


def test_proc_mem_reads_known_child_memory():
    check_child_read(proc_read)


def test_process_vm_reads_known_child_memory():
    check_child_read(vm_read)


def test_failed_probe_is_logged_and_watchable():
    with tempfile.TemporaryDirectory() as directory:
        base = [sys.executable, '-m', 'inventory_tracking', '--output', directory]
        run = subprocess.run([*base, 'probe', '--pid', str(os.getpid())], capture_output=True, text=True)
        assert run.returncode == 1
        (report_path,) = Path(directory).glob('*/report.json')
        report = json.loads(report_path.read_text())
        assert report['state'] == 'failed'
        assert 'not identifiable' in report['error']['error']
        assert 'Probe failed' in (report_path.parent / 'probe.log').read_text()
        watch = subprocess.run([*base, 'watch', '--include-existing', '--timeout', '2'], capture_output=True, text=True)
        assert watch.returncode == 1
        assert json.loads(watch.stdout)['run_id'] == report['run_id']
        old = subprocess.run([*base, 'watch', '--timeout', '0.1'], capture_output=True, text=True)
        assert old.returncode == 124


def test_watcher_detects_running_then_complete():
    with tempfile.TemporaryDirectory() as directory:
        command = [sys.executable, '-m', 'inventory_tracking', '--output', directory, 'watch', '--timeout', '5']
        watcher = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stderr = watcher.stderr
            assert stderr is not None
            # The first log is emitted after the baseline scan: no race with creating the run.
            assert 'Watching' in stderr.readline()
            run = Path(directory) / 'new-run'
            run.mkdir()
            path = run / 'report.json'
            publish(path, {'state': 'running'})
            assert 'Detected run' in stderr.readline()
            publish(path, {'state': 'complete', 'exit_code': 0, 'run_id': 'new-run'})
            out, _ = watcher.communicate(timeout=5)
            assert watcher.returncode == 0
            assert json.loads(out)['run_id'] == 'new-run'
        finally:
            if watcher.poll() is None:
                watcher.terminate()
                watcher.communicate(timeout=5)
